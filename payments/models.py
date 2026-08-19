from django.db import models
from core.models import TenantModel

class Payment(TenantModel):
    METHOD_CHOICES = (
        ('UPI', 'UPI Payment'),
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Online', 'Online Payment Gateway'),
    )

    STATUS_CHOICES = (
        ('Paid', 'Paid'),
        ('Pending', 'Pending'),
        ('Failed', 'Failed'),
    )

    VERIFICATION_CHOICES = (
        ('Verified', 'Verified'),
        ('Payment Claimed', 'Payment Claimed'),
        ('Pending Verification', 'Pending Verification'),
        ('Paid', 'Paid'),
    )

    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='payments')
    udhaar = models.ForeignKey('udhaar.Udhaar', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    sale = models.ForeignKey('sales.Sale', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=METHOD_CHOICES, default='UPI')
    reference_id = models.CharField(max_length=100, blank=True, verbose_name="Reference / UTR #")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Paid')
    verification_status = models.CharField(max_length=30, choices=VERIFICATION_CHOICES, default='Verified')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment #{self.id} - {self.customer.name} ({self.amount})"
