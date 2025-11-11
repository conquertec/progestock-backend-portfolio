from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VerifyCodeView,
    ResendVerificationCodeView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    PasswordResetVerifyCodeView,
    UserProfileView,
    # Team management views
    TeamViewSet,
    InviteView,
    ResendInvitationView,
    AcceptInvitationView,
    ValidateInvitationView,
    # Settings views
    UserProfileDetailView,
    ChangePasswordAPIView,
    # Debug views
    DebugCookieSettingsView,
)

# Create a router for the ViewSet
router = DefaultRouter()
router.register(r'team', TeamViewSet, basename='team')

urlpatterns = [
    # User authentication endpoints
    path('verify-code/', VerifyCodeView.as_view(), name='verify-code'),
    path('resend-code/', ResendVerificationCodeView.as_view(), name='resend-code'),
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/verify-code/', PasswordResetVerifyCodeView.as_view(), name='password-reset-verify-code'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),

    # Team management endpoints
    path('invitations/', InviteView.as_view(), name='team-invitations'),
    path('invitations/<uuid:invitation_id>/resend/', ResendInvitationView.as_view(), name='resend-invitation'),
    path('invitations/accept/', AcceptInvitationView.as_view(), name='accept-invitation'),
    path('invitations/validate/', ValidateInvitationView.as_view(), name='validate-invitation'),

    # Settings endpoints
    path('settings/profile/', UserProfileDetailView.as_view(), name='user-profile-settings'),
    path('settings/change-password/', ChangePasswordAPIView.as_view(), name='change-password'),

    # Debug endpoints (remove after debugging)
    path('debug/cookie-settings/', DebugCookieSettingsView.as_view(), name='debug-cookie-settings'),

    # Include router URLs for team management
    path('', include(router.urls)),
]

