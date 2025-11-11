"""
URL configuration for progestock_backend project.
"""
from django.contrib import admin
from django.urls import path, include
from dj_rest_auth.views import LogoutView, PasswordResetView, PasswordResetConfirmView, UserDetailsView
from rest_framework_simplejwt.views import TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from user.views import GoogleLoginView, CustomRegisterView, CustomLoginView

# Root API endpoint
def api_root(request):
    return JsonResponse({
        'message': 'Progestock API is running successfully',
        'version': '1.0.0',
        'status': 'online',
        'endpoints': {
            'authentication': {
                'login': '/api/auth/login/',
                'logout': '/api/auth/logout/',
                'register': '/api/auth/registration/',
                'google_login': '/api/auth/google/',
                'user_details': '/api/auth/user/',
                'token_refresh': '/api/auth/token/refresh/',
                'password_reset': '/api/auth/password/reset/',
            },
            'resources': {
                'dashboard': '/api/dashboard/',
                'user': '/api/user/',
                'company': '/api/company/',
                'inventory': '/api/inventory/',
                'sales': '/api/sales/',
                'purchasing': '/api/purchasing/',
                'reports': '/api/reports/',
                'notifications': '/api/notifications/',
            },
            'admin': '/admin/',
        },
        'documentation': 'Contact your administrator for API documentation'
    })

# Health check endpoint for monitoring and keeping service awake
@csrf_exempt  # Allow monitoring tools to ping without CSRF token
@require_http_methods(["GET", "HEAD"])  # Only allow GET and HEAD requests
def health_check(request):
    """
    Lightweight health check endpoint for UptimeRobot and other monitoring services.
    Returns 200 OK if the service is running.
    """
    return JsonResponse({
        'status': 'healthy',
        'service': 'progestock-backend',
        'timestamp': __import__('datetime').datetime.now().isoformat()
    })

# Debug endpoint to check CORS and cookie configuration
def debug_cors(request):
    """Debug endpoint to verify CORS headers and cookie settings"""
    from django.conf import settings
    return JsonResponse({
        'origin': request.META.get('HTTP_ORIGIN', 'No origin header'),
        'cookies_received': list(request.COOKIES.keys()),
        'cors_allowed_origins': settings.CORS_ALLOWED_ORIGINS if hasattr(settings, 'CORS_ALLOWED_ORIGINS') else [],
        'cors_allow_credentials': settings.CORS_ALLOW_CREDENTIALS if hasattr(settings, 'CORS_ALLOW_CREDENTIALS') else False,
        'is_production': not settings.DEBUG,
        'session_cookie_samesite': settings.SESSION_COOKIE_SAMESITE,
        'session_cookie_secure': settings.SESSION_COOKIE_SECURE,
        'authenticated': request.user.is_authenticated,
        'user_email': request.user.email if request.user.is_authenticated else None,
    })

urlpatterns = [
    # Root endpoint
    path('', api_root, name='api_root'),

    # Health check endpoint (for monitoring and keeping service awake)
    path('health/', health_check, name='health_check'),

    # Debug endpoint (remove in production after fixing issues)
    path('debug/cors/', debug_cors, name='debug_cors'),

    path('admin/', admin.site.urls),

    # --- Authentication URLs (MUST come before dj_rest_auth.urls to override defaults) ---
    path('api/auth/login/', CustomLoginView.as_view(), name='rest_login'),
    path('api/auth/logout/', LogoutView.as_view(), name='rest_logout'),
    path('api/auth/user/', UserDetailsView.as_view(), name='rest_user_details'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/password/reset/', PasswordResetView.as_view(), name='rest_password_reset'),
    path('api/auth/password/reset/confirm/', PasswordResetConfirmView.as_view(), name='rest_password_reset_confirm'),
    path('api/auth/registration/', CustomRegisterView.as_view(), name='rest_register'),
    path('api/auth/google/', GoogleLoginView.as_view(), name='google_login'),

    # Include remaining dj_rest_auth URLs (after custom overrides)
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/dashboard/', include('dashboard.urls')),

    # --- App-specific URLs ---
    path('api/user/', include('user.urls')),
    path('api/company/', include('company.urls')),
    path('api/inventory/', include('inventory.urls')),
    path('api/sales/', include('sales.urls')),
    path('api/purchasing/', include('purchasing.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/notifications/', include('notifications.urls')),
    
    # This is for django-allauth internal views
    path('accounts/', include('allauth.urls')),
]

# Serve media files during development
# In production, whitenoise will handle serving media files if configured.
# In development, this allows the Django dev server to serve them.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# This is a safer way that still works for both dev and prod with whitenoise
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)