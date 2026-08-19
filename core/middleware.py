class TenantMiddleware:
    """
    Middleware that sets request.business based on the logged-in user's UserProfile.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.business = None
        if request.user.is_authenticated:
            if hasattr(request.user, 'profile') and request.user.profile.business:
                request.business = request.user.profile.business
        
        response = self.get_response(request)
        return response
