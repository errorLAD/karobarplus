import json
import datetime
from django.shortcuts import render
from django.views import View
from django.db.models import Sum, Count, Q
from django.utils import timezone

from core.mixins import TenantRequiredMixin
from sales.models import Sale, SaleItem
from udhaar.models import Udhaar
from customers.models import Customer
from products.models import Product
from payments.models import Payment
from whatsapp.models import WhatsAppMessage
from suppliers.models import Supplier, SupplierPurchase, SupplierPayment

class DashboardIndexView(TenantRequiredMixin, View):
    def get(self, request):
        business = request.business
        today = timezone.now().date()
        first_day_of_month = today.replace(day=1)

        # 1. Sales Aggregations
        all_sales = Sale.objects.filter(business=business)
        todays_sales = all_sales.filter(sale_date__date=today).aggregate(s=Sum('total_amount'))['s'] or 0
        months_sales = all_sales.filter(sale_date__date__gte=first_day_of_month).aggregate(s=Sum('total_amount'))['s'] or 0
        total_sales = all_sales.aggregate(s=Sum('total_amount'))['s'] or 0

        # 2. Customer Udhaar (Receivable) Aggregations
        all_udhaars = Udhaar.objects.filter(business=business)
        total_outstanding = all_udhaars.exclude(status='Paid').aggregate(s=Sum('remaining_amount'))['s'] or 0
        overdue_amount = all_udhaars.filter(due_date__lt=today).exclude(status='Paid').aggregate(s=Sum('remaining_amount'))['s'] or 0
        due_today_count = all_udhaars.filter(due_date=today).exclude(status='Paid').count()
        amount_recovered = all_udhaars.aggregate(s=Sum('paid_amount'))['s'] or 0

        # 3. Supplier Udhaar (Payable) Aggregations
        all_suppliers = Supplier.objects.filter(business=business)
        total_suppliers = all_suppliers.count()
        suppliers_owed_count = sum(1 for s in all_suppliers if s.outstanding_payable > 0)

        active_supplier_purchases = SupplierPurchase.objects.filter(business=business).exclude(status='Paid')
        total_supplier_payable = sum([p.remaining_payable for p in active_supplier_purchases])
        overdue_supplier_payable = sum([p.remaining_payable for p in active_supplier_purchases.filter(status='Overdue')])
        supplier_due_today_count = active_supplier_purchases.filter(due_date=today).count()
        supplier_due_soon_count = active_supplier_purchases.filter(due_date__gt=today, due_date__lte=today + datetime.timedelta(days=7)).count()
        paid_supplier_this_month = SupplierPayment.objects.filter(business=business, date__date__gte=first_day_of_month).aggregate(s=Sum('amount'))['s'] or 0

        # 4. Money Position Calculation
        customer_receivable = float(total_outstanding)
        supplier_payable = float(total_supplier_payable)
        net_receivable_position = round(customer_receivable - supplier_payable, 2)

        # 5. Customer Aggregations
        all_customers = Customer.objects.filter(business=business)
        total_customers = all_customers.count()
        customers_with_udhaar = sum(1 for c in all_customers if c.get_outstanding_udhaar > 0)

        # 6. Product / Inventory Aggregations
        all_products = Product.objects.filter(business=business)
        total_products = all_products.count()
        low_stock_count = sum(1 for p in all_products if p.is_low_stock)
        out_of_stock_count = sum(1 for p in all_products if p.is_out_of_stock)

        # 7. Combined Activity Feed & Upcoming Money Flow
        recent_sales = list(all_sales.order_by('-sale_date')[:5])
        recent_payments = list(Payment.objects.filter(business=business).order_by('-created_at')[:5])
        recent_udhaars = list(all_udhaars.order_by('-created_at')[:5])
        recent_supplier_payments = list(SupplierPayment.objects.filter(business=business).order_by('-created_at')[:5])
        recent_wa_messages = list(WhatsAppMessage.objects.filter(conversation__business=business).order_by('-timestamp')[:5])

        upcoming_supplier_payments = active_supplier_purchases.filter(due_date__isnull=False).order_by('due_date')[:5]
        upcoming_customer_receivables = all_udhaars.exclude(status='Paid').order_by('due_date')[:5]

        # 8. Chart.js Datasets
        sales_chart_labels = []
        sales_chart_data = []
        for i in range(6, -1, -1):
            d = today - datetime.timedelta(days=i)
            sales_chart_labels.append(d.strftime('%d %b'))
            val = all_sales.filter(sale_date__date=d).aggregate(s=Sum('total_amount'))['s'] or 0
            sales_chart_data.append(float(val))

        udhaar_pie_labels = ['Recovered Amount', 'Remaining Outstanding']
        udhaar_pie_data = [float(amount_recovered), float(total_outstanding)]

        top_products_qs = SaleItem.objects.filter(sale__business=business)\
                                          .values('product_name')\
                                          .annotate(total_qty=Sum('quantity'))\
                                          .order_by('-total_qty')[:5]
        top_product_labels = [item['product_name'] for item in top_products_qs]
        top_product_data = [item['total_qty'] for item in top_products_qs]

        context = {
            'todays_sales': todays_sales,
            'months_sales': months_sales,
            'total_sales': total_sales,

            'total_outstanding': total_outstanding,
            'overdue_amount': overdue_amount,
            'due_today_count': due_today_count,
            'amount_recovered': amount_recovered,

            'total_suppliers': total_suppliers,
            'suppliers_owed_count': suppliers_owed_count,
            'total_supplier_payable': total_supplier_payable,
            'overdue_supplier_payable': overdue_supplier_payable,
            'supplier_due_today_count': supplier_due_today_count,
            'supplier_due_soon_count': supplier_due_soon_count,
            'paid_supplier_this_month': paid_supplier_this_month,

            'customer_receivable': customer_receivable,
            'supplier_payable': supplier_payable,
            'net_receivable_position': net_receivable_position,

            'total_customers': total_customers,
            'customers_with_udhaar': customers_with_udhaar,

            'total_products': total_products,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,

            'recent_sales': recent_sales,
            'recent_payments': recent_payments,
            'recent_udhaars': recent_udhaars,
            'recent_supplier_payments': recent_supplier_payments,
            'recent_wa_messages': recent_wa_messages,
            'upcoming_supplier_payments': upcoming_supplier_payments,
            'upcoming_customer_receivables': upcoming_customer_receivables,

            'sales_chart_labels': json.dumps(sales_chart_labels),
            'sales_chart_data': json.dumps(sales_chart_data),
            'udhaar_pie_labels': json.dumps(udhaar_pie_labels),
            'udhaar_pie_data': json.dumps(udhaar_pie_data),
            'top_product_labels': json.dumps(top_product_labels),
            'top_product_data': json.dumps(top_product_data),
        }

        return render(request, 'dashboard/dashboard.html', context)
