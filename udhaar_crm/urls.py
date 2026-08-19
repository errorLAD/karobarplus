from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

def root_redirect(request):
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_staff:
            return redirect('platform_admin:dashboard')
        return redirect('dashboard:index')
    return redirect('accounts:login')

urlpatterns = [
    path('', root_redirect, name='root'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('customers/', include('customers.urls', namespace='customers')),
    path('sales/', include('sales.urls', namespace='sales')),
    path('udhaar/', include('udhaar.urls', namespace='udhaar')),
    path('suppliers/', include('suppliers.urls', namespace='suppliers')),
    path('products/', include('products.urls', namespace='products')),
    path('ai-advisor/', include('ai_advisor.urls', namespace='ai_advisor')),
    path('whatsapp/', include('whatsapp.urls', namespace='whatsapp')),
    path('promotions/', include('promotions.urls', namespace='promotions')),
    path('sales-agent/', include('sales_agent.urls', namespace='sales_agent')),
    path('platform-admin/', include('platform_admin.urls', namespace='platform_admin')),
    path('payments/', include('payments.urls', namespace='payments')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('settings/', include('settings_app.urls', namespace='settings_app')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
