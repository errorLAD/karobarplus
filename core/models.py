from django.db import models

class TenantQuerySet(models.QuerySet):
    def for_business(self, business):
        if business:
            return self.filter(business=business)
        return self.none()

class TenantManager(models.Manager):
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def for_business(self, business):
        return self.get_queryset().for_business(business)

class TenantModel(models.Model):
    business = models.ForeignKey(
        'accounts.Business',
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        verbose_name='Business Tenant'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        abstract = True
