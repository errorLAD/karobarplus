from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from core.mixins import TenantRequiredMixin
from .models import Customer
from .forms import CustomerForm
from whatsapp.models import Tag

class CustomerListView(TenantRequiredMixin, ListView):
    model = Customer
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset()
        search_query = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', '').strip()
        has_udhaar = self.request.GET.get('has_udhaar', '').strip()
        tag_filter = self.request.GET.get('tag', '').strip()
        risk_filter = self.request.GET.get('risk', '').strip()

        if search_query:
            qs = qs.filter(Q(name__icontains=search_query) | Q(phone__icontains=search_query) | Q(address__icontains=search_query))
        if status_filter:
            qs = qs.filter(status=status_filter)
        if tag_filter:
            qs = qs.filter(tags__id=tag_filter)
        
        if has_udhaar == 'yes':
            qs = [c for c in qs if c.get_outstanding_udhaar > 0]

        if risk_filter:
            qs = [c for c in qs if c.risk_score['level'].lower().startswith(risk_filter.lower())]

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['has_udhaar'] = self.request.GET.get('has_udhaar', '')
        context['tag_filter'] = self.request.GET.get('tag', '')
        context['risk_filter'] = self.request.GET.get('risk', '')
        context['all_tags'] = Tag.objects.filter(business=self.request.business)
        return context

class CustomerCreateView(TenantRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['business'] = self.request.business
        return kwargs

    def form_valid(self, form):
        form.instance.business = self.request.business
        messages.success(self.request, f"Customer '{form.instance.name}' created successfully!")
        return super().form_valid(form)

class CustomerUpdateView(TenantRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['business'] = self.request.business
        return kwargs

    def get_success_url(self):
        return reverse_lazy('customers:detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Customer details updated!")
        return super().form_valid(form)

class CustomerDetailView(TenantRequiredMixin, DetailView):
    model = Customer
    template_name = 'customers/customer_detail.html'
    context_object_name = 'customer'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.object

        # Sales History
        sales = customer.sales.all().order_by('-sale_date')
        context['sales'] = sales

        # Payments History
        payments = customer.payments.all().order_by('-created_at')
        context['payments'] = payments

        # Udhaar History
        udhaars = customer.udhaars.all().order_by('-created_at')
        context['udhaars'] = udhaars

        # Referrals list
        context['referrals'] = customer.referrals.all()
        context['all_tags'] = Tag.objects.filter(business=self.request.business)

        # Products for Khata inline form
        from products.models import Product
        context['products'] = Product.objects.filter(business=self.request.business)

        # WhatsApp Messages
        from whatsapp.models import WhatsAppMessage, WhatsAppConversation
        conv = WhatsAppConversation.objects.filter(business=self.request.business, customer=customer).first()
        messages_qs = conv.messages.all().order_by('-timestamp')[:20] if conv else []
        context['whatsapp_messages'] = messages_qs
        context['whatsapp_conversation'] = conv

        # Combined Customer Timeline
        timeline_items = []
        for s in sales:
            timeline_items.append({
                'type': 'sale',
                'title': f"Sale Recorded #{s.invoice_number}",
                'amount': s.total_amount,
                'description': f"Paid {s.paid_amount}, Udhaar {s.udhaar_amount}",
                'timestamp': s.sale_date
            })
        for u in udhaars:
            timeline_items.append({
                'type': 'udhaar',
                'title': f"Udhaar Outstanding Created",
                'amount': u.remaining_amount,
                'description': f"Due on {u.due_date} (Status: {u.status})",
                'timestamp': u.created_at
            })
        for p in payments:
            timeline_items.append({
                'type': 'payment',
                'title': f"Payment Received ({p.payment_method})",
                'amount': p.amount,
                'description': f"Ref: {p.reference_id or 'Cash'} - Status: {p.status}",
                'timestamp': p.created_at
            })
        if conv:
            for m in conv.messages.all():
                desc = m.message_text
                if m.is_voice_note:
                    desc = f"🎤 Voice Note Transcript: {m.transcript or desc}"
                timeline_items.append({
                    'type': 'whatsapp',
                    'title': f"WhatsApp {m.sender.title()}",
                    'amount': None,
                    'description': desc,
                    'timestamp': m.timestamp
                })

        timeline_items.sort(key=lambda x: x['timestamp'], reverse=True)
        context['timeline'] = timeline_items[:30]

        return context
