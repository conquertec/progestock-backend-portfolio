from django.urls import path
from .views import (
    DashboardStatisticsView,
    LowStockItemsView,
    RecentActivitiesView,
    TopProductsView,
    SalesTrendView
)

urlpatterns = [
    path('statistics/', DashboardStatisticsView.as_view(), name='dashboard-statistics'),
    path('low-stock/', LowStockItemsView.as_view(), name='dashboard-low-stock'),
    path('activities/', RecentActivitiesView.as_view(), name='dashboard-activities'),
    path('top-products/', TopProductsView.as_view(), name='dashboard-top-products'),
    path('sales-trend/', SalesTrendView.as_view(), name='dashboard-sales-trend'),
]