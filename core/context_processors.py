def tenant_context(request):
    """
    Context processor to pass business and unread notifications count to all templates.
    """
    context = {
        'current_business': getattr(request, 'business', None),
        'unread_notifications_count': 0,
        'recent_notifications': [],
    }
    if request.user.is_authenticated and getattr(request, 'business', None):
        try:
            from notifications.models import Notification
            context['unread_notifications_count'] = Notification.objects.filter(
                business=request.business,
                is_read=False
            ).count()
            context['recent_notifications'] = Notification.objects.filter(
                business=request.business
            ).order_by('-created_at')[:5]
        except Exception:
            pass
    return context
