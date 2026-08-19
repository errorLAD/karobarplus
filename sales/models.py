from django.db import models
from core.models import TenantModel

class Sale(TenantModel):
    PAYMENT_METHOD_CHOICES = (
        ('Cash', 'Cash'),
        ('UPI', 'UPI Payment'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Udhaar / Credit', 'Udhaar / Credit'),
    )
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='sales')
    invoice_number = models.CharField(max_length=50, verbose_name="Invoice #")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    udhaar_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='Cash')
    sale_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-sale_date']

    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.customer.name} ({self.total_amount})"

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.SET_NULL, null=True, blank=True, related_name='sale_items')
    product_name = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
