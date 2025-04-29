from django.conf import settings

class AdminSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            # If path is /admin/, use a different session cookie
            settings.SESSION_COOKIE_NAME = 'admin_sessionid'
        else:
            # Otherwise, use normal session for frontend
            settings.SESSION_COOKIE_NAME = 'frontend_sessionid'
        
        response = self.get_response(request)
        return response
