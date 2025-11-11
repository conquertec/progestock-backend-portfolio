# middleware.py
class CORSCookieMiddleware:
    """
    Middleware to ensure cookies work with CORS in production
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Only in production
        if not __debug__:  # This is False when DEBUG=False
            origin = request.headers.get('Origin')
            allowed_origins = [
                'https://progestockweb-app-levy-ogelets-projects.vercel.app'
            ]
            
            if origin in allowed_origins:
                response['Access-Control-Allow-Origin'] = origin
                response['Access-Control-Allow-Credentials'] = 'true'
                response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
                response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRFToken'
        
        return response