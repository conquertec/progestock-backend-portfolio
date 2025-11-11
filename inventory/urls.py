from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LocationViewSet,
    CategoryViewSet,
    ClientViewSet,
    DashboardStatsView,
    ProductViewSet,
    StockViewSet,
    ProductBulkImportView,
    StockControlOverviewView,
    StockAdjustmentView,
    StockTransferView,
    StockHistoryView
)

# 1. Create a router to automatically handle the URLs for our ViewSets.
router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'stock', StockViewSet, basename='stock')
router.register(r'locations', LocationViewSet, basename='location')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'clients', ClientViewSet, basename='client')

urlpatterns = [
    path('products/bulk-import/', ProductBulkImportView.as_view(), name='product-bulk-import'),

    # This is the endpoint for your dashboard KPIs.
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),

    # Stock Control endpoints
    path('stock-control/overview/', StockControlOverviewView.as_view(), name='stock-control-overview'),
    path('stock-control/adjust/', StockAdjustmentView.as_view(), name='stock-adjustment'),
    path('stock-control/transfer/', StockTransferView.as_view(), name='stock-transfer'),
    path('stock-control/history/', StockHistoryView.as_view(), name='stock-history'),

    path('', include(router.urls)),
]

