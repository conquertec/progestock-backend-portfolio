from django.urls import path
from .views import SalesReportView, InventoryValuationView, QuoteConversionView

urlpatterns = [
    path('sales/', SalesReportView.as_view(), name='sales-report'),
    path('inventory-valuation/', InventoryValuationView.as_view(), name='inventory-valuation'),
    path('quote-conversion/', QuoteConversionView.as_view(), name='quote-conversion'),
]
