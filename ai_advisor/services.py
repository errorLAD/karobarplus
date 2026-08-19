import json
import datetime
from django.utils import timezone
from .models import AIBusinessInsightCache, AIAdvisorQueryLog
from .analytics import (
    get_date_bounds, build_structured_analytics_payload,
    get_business_health_summary, get_udhaar_recovery_insights,
    get_todays_priority_contacts, get_sales_velocity_and_slow_inventory,
    get_restock_recommendations
)
from .llm_provider import call_llm_api

def generate_business_insights(business, period_code='30_days', custom_start=None, custom_end=None, force_refresh=False):
    """
    Retrieves cached business insights or computes structured analytics payload.
    """
    cache_entry = AIBusinessInsightCache.objects.filter(business=business, date_range_code=period_code).first()

    if cache_entry and not force_refresh:
        age_seconds = (timezone.now() - cache_entry.last_analyzed_at).total_seconds()
        if age_seconds < 3600 and cache_entry.insight_json:
            return cache_entry.insight_json

    start_date, end_date = get_date_bounds(period_code, custom_start, custom_end)
    payload = build_structured_analytics_payload(business, start_date, end_date)

    # Optional LLM Enhancement if configured
    try:
        from settings_app.models import BusinessSettings
        b_settings = BusinessSettings.objects.filter(business=business).first()
        if b_settings and b_settings.is_ai_enabled and b_settings.ai_api_key:
            system_prompt = (
                "You are an expert AI Business Advisor for an Indian Kirana/SMB store. "
                "Analyze the provided structured CRM database context. "
                "Provide a concise, 2-sentence executive summary of business health, highlight key risks, and recommend 2 immediate actions. "
                "Never invent numbers or facts not present in the data."
            )
            user_prompt = f"BUSINESS CRM ANALYTICS CONTEXT:\n{json.dumps(payload, indent=2)}"
            llm_summary = call_llm_api(b_settings, system_prompt, user_prompt)
            if llm_summary and len(llm_summary.strip()) > 10:
                payload['business_health']['summary'] = f"[AI Generated ({b_settings.get_ai_provider_display()})]: {llm_summary.strip()}"
    except Exception:
        # Fall back gracefully to standard ORM computed summary
        pass

    # Save to cache
    if not cache_entry:
        cache_entry = AIBusinessInsightCache(
            business=business,
            date_range_code=period_code
        )
    
    cache_entry.health_status = payload['business_health']['status']
    cache_entry.health_summary = payload['business_health']['summary']
    cache_entry.insight_json = payload
    cache_entry.save()

    return payload

def answer_business_question(business, question_text):
    """
    Answers business questions using real DB analytics context + optional LLM integration.
    """
    text = question_text.lower().strip()
    today = timezone.now().date()
    start_date = today - datetime.timedelta(days=30)

    payload = build_structured_analytics_payload(business, start_date, today)

    # Try LLM API first if configured
    llm_answer = None
    try:
        from settings_app.models import BusinessSettings
        b_settings = BusinessSettings.objects.filter(business=business).first()
        if b_settings and b_settings.is_ai_enabled and b_settings.ai_api_key:
            system_prompt = (
                "You are an expert AI Business Advisor for an Indian SMB store. "
                "Use ONLY the provided CRM database analytics payload to answer the owner's question. "
                "Format your answer strictly as: "
                "Insight: ... | Evidence: ... | Reasoning: ... | Action: ... "
                "Never invent numbers, customers, sales, or payments."
            )
            user_prompt = f"STORE ANALYTICS DATA:\n{json.dumps(payload, indent=2)}\n\nOWNER QUESTION:\n{question_text}"
            llm_reply = call_llm_api(b_settings, system_prompt, user_prompt)
            if llm_reply and len(llm_reply.strip()) > 15:
                llm_answer = f"🤖 [{b_settings.get_ai_provider_display()} AI Advisor Response]:\n{llm_reply.strip()}"
    except Exception:
        pass

    if llm_answer:
        resp = llm_answer
        link_url = "/ai-advisor/"
        link_text = "View Dashboard"
    else:
        # Fallback to high-accuracy rule-based parser
        if any(k in text for k in ['udhaar', 'credit', 'outstanding', 'overdue', 'money', 'paise']):
            u_sum = payload['udhaar_summary']
            resp = (
                f"Insight: Total outstanding udhaar is ₹{u_sum['total_outstanding']:,.2f}, out of which ₹{u_sum['total_overdue']:,.2f} is overdue. "
                f"Evidence: {u_sum['broken_promises_cnt']} payment promises have been broken recently. "
                f"Reasoning: Overdue accounts are growing faster than payment settlements. "
                f"Action: Contact today's priority accounts first and pause extending additional credit until previous balances are reduced."
            )
            link_url = "/udhaar/"
            link_text = "View Udhaar Accounts"

        elif any(k in text for k in ['fast', 'selling', 'top product', 'popular', 'best selling']):
            fast_list = payload['fast_moving_products']
            if fast_list:
                top_str = ", ".join([f"'{p['product_name']}' ({p['units_sold']} units)" for p in fast_list[:3]])
                resp = f"Insight: Fast-moving items in the last 30 days are: {top_str}. " \
                       f"Action: Keep sufficient inventory of these high-velocity items to avoid stockouts."
            else:
                resp = "Insight: No high-velocity sales recorded in the last 30 days."
            link_url = "/products/"
            link_text = "View Products"

        elif any(k in text for k in ['restock', 'buy', 'stockout', 'shortage', 'low stock']):
            restock_list = payload['restock_recommendations']
            if restock_list:
                r_str = ", ".join([f"'{r['product_name']}' (stock: {r['current_stock']})" for r in restock_list[:3]])
                resp = f"Insight: Restock recommended for {r_str}. " \
                       f"Reasoning: Current inventory is at or below minimum threshold. " \
                       f"Action: Place restock orders soon."
            else:
                resp = "Insight: All active products currently have sufficient inventory above minimum low-stock thresholds."
            link_url = "/products/"
            link_text = "View Product Catalog"

        elif any(k in text for k in ['supplier', 'payable', 'owe', 'vendor']):
            s_pay = payload.get('supplier_payables', {})
            top_s = s_pay.get('top_suppliers_owed', [])
            s_str = f" Total supplier payable is ₹{s_pay.get('total_payable', 0):,.2f}, out of which ₹{s_pay.get('overdue_payable', 0):,.2f} is overdue."
            if top_s:
                s_str += f" Top supplier owed: {top_s[0]['supplier_name']} (₹{top_s[0]['outstanding_payable']:,.2f})."
            resp = f"Insight:{s_str} Action: Review upcoming supplier due dates and balance cash flow before placing new credit orders."
            link_url = "/suppliers/payables/"
            link_text = "View Supplier Payables"

        elif any(k in text for k in ['contact', 'who', 'call', 'today', 'priority']):
            priorities = payload['priority_contacts']
            if priorities:
                c_names = ", ".join([f"{p['customer_name']} (₹{p['outstanding']:,.2f})" for p in priorities[:3]])
                resp = f"Insight: Top priority contacts today: {c_names}. " \
                       f"Action: Reach out via phone or WhatsApp with direct UPI payment links."
            else:
                resp = "Insight: No high-risk overdue accounts require urgent contact today."
            link_url = "/customers/"
            link_text = "View Customers"

        else:
            h = payload['business_health']
            resp = f"Insight: Business Health Status is '{h['status']}'. {h['summary']}"
            link_url = "/ai-advisor/"
            link_text = "View AI Advisor Dashboard"

    # Log query
    AIAdvisorQueryLog.objects.create(
        business=business,
        question=question_text,
        answer=resp
    )

    return {
        'question': question_text,
        'answer': resp,
        'link_url': link_url,
        'link_text': link_text
    }
