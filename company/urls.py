from django.urls import path
from .views import (
    CompanyOnboardingView,
    CompleteOnboardingView,
    CompanySettingsView,
    GenerateProfileView
)

urlpatterns = [
    # Onboarding endpoints
    path('onboarding/', CompanyOnboardingView.as_view(), name='company-onboarding'),
    path('onboarding/complete/', CompleteOnboardingView.as_view(), name='complete-onboarding'),
    path('generate-profile/', GenerateProfileView.as_view(), name='generate-profile'),

    # Settings endpoints
    path('settings/', CompanySettingsView.as_view(), name='company-settings'),
]