from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuoteViewSet, InvoiceViewSet

router = DefaultRouter()
router.register(r'quotes', QuoteViewSet, basename='quote')
router.register(r'invoices', InvoiceViewSet, basename='invoice')

urlpatterns = [
    path('', include(router.urls)),
]
