from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Count
from django.utils import timezone
from datetime import timedelta

# Import the models we need to query
from inventory.models import Product, Stock, Client
from auditing.models import LogEntry
from .models import Sale, SaleItem

class DashboardStatisticsView(APIView):
    """
    Provides the Key Performance Indicators (KPIs) for the main dashboard.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request, *args, **kwargs):
        company = request.user.company
        if not company:
            return Response({"error": "User is not associated with a company."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Total Stock Value
        total_stock_value = Stock.objects.filter(product__company=company).annotate(
            item_value=ExpressionWrapper(F('quantity') * F('product__price'), output_field=DecimalField())
        ).aggregate(total_value=Sum('item_value'))['total_value'] or 0

        # 2. Low Stock Alerts Count
        low_stock_alerts = Stock.objects.filter(
            product__company=company, 
            quantity__lte=F('product__reorder_threshold')
        ).count()

        # 3. & 4. Placeholders for Sales data (we will build these models next)
        pending_quotes_value = 0 
        overdue_invoices_value = 0

        kpis = {
            "total_stock_value": total_stock_value,
            "low_stock_alerts": low_stock_alerts,
            "pending_quotes_value": pending_quotes_value,
            "overdue_invoices_value": overdue_invoices_value,
        }
        return Response(kpis, status=status.HTTP_200_OK)


class LowStockItemsView(APIView):
    """
    Provides a list of products that are at or below their reorder threshold.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request, *args, **kwargs):
        company = request.user.company

        # Get limit from query params, default to 10
        limit = int(request.query_params.get('limit', 10))

        low_stock_items = Stock.objects.filter(
            product__company=company,
            quantity__lte=F('product__reorder_threshold')
        ).select_related('product', 'location').order_by('quantity')[:limit]

        data = [{
            "product_name": item.product.name,
            "sku": item.product.sku,
            "location_name": item.location.name,
            "quantity": item.quantity,
            "threshold": item.product.reorder_threshold,
        } for item in low_stock_items]
        
        return Response(data, status=status.HTTP_200_OK)


class RecentActivitiesView(APIView):
    """
    Provides a list of the most recent audit log entries for the user's company.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request, *args, **kwargs):
        company = request.user.company

        # Get limit from query params, default to 10
        limit = int(request.query_params.get('limit', 10))

        activities = LogEntry.objects.filter(company=company).select_related('user').order_by('-timestamp')[:limit]

        data = []
        for activity in activities:
            activity_data = {
                "user_email": activity.user.email if activity.user else "System",
                "action_type": activity.action_type,
                "timestamp": activity.timestamp,
                "details": activity.details,
            }

            # Include user profile information if available
            if activity.user:
                activity_data["user_first_name"] = activity.user.first_name
                activity_data["user_last_name"] = activity.user.last_name
                # Include profile picture URL if it exists
                if hasattr(activity.user, 'profile_picture') and activity.user.profile_picture:
                    # Check if it's already a URL string or an ImageField
                    if isinstance(activity.user.profile_picture, str):
                        # Already a URL string
                        activity_data["user_avatar"] = activity.user.profile_picture
                    else:
                        # It's an ImageField, get the URL
                        try:
                            activity_data["user_avatar"] = request.build_absolute_uri(activity.user.profile_picture.url)
                        except (ValueError, AttributeError):
                            activity_data["user_avatar"] = None
                else:
                    activity_data["user_avatar"] = None
            else:
                activity_data["user_first_name"] = None
                activity_data["user_last_name"] = None
                activity_data["user_avatar"] = None

            data.append(activity_data)

        return Response(data, status=status.HTTP_200_OK)


class TopProductsView(APIView):
    """
    Provides a list of top-selling products based on sales data.
    Falls back to top stocked products if no sales data exists.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request, *args, **kwargs):
        company = request.user.company
        if not company:
            return Response({"error": "User is not associated with a company."}, status=status.HTTP_400_BAD_REQUEST)

        # Get limit from query params, default to 5
        limit = int(request.query_params.get('limit', 5))

        # Try to get top products by sales
        top_products = SaleItem.objects.filter(
            sale__company=company,
            sale__status='completed'
        ).values('product__id', 'product__name', 'product__sku').annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('subtotal')
        ).order_by('-total_quantity')[:limit]

        # If no sales data, fall back to products with highest stock levels
        if not top_products:
            top_products = Stock.objects.filter(
                product__company=company
            ).values('product__id', 'product__name', 'product__sku').annotate(
                total_quantity=Sum('quantity')
            ).order_by('-total_quantity')[:limit]

            data = [{
                "product_id": item['product__id'],
                "product_name": item['product__name'],
                "sku": item['product__sku'],
                "total_stock": item['total_quantity'],
                "total_revenue": 0,
            } for item in top_products]
        else:
            data = [{
                "product_id": item['product__id'],
                "product_name": item['product__name'],
                "sku": item['product__sku'],
                "total_sold": item['total_quantity'],
                "total_revenue": float(item.get('total_revenue', 0)),
            } for item in top_products]

        return Response(data, status=status.HTTP_200_OK)


class SalesTrendView(APIView):
    """
    Provides sales trend data over a specified time period.
    Combines data from both Sale model and paid Invoices.
    Supports: 7days, 30days, 90days, 1year
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request, *args, **kwargs):
        from sales.models import Invoice
        from datetime import datetime, timedelta as dt_timedelta
        from collections import defaultdict

        company = request.user.company
        if not company:
            return Response({"error": "User is not associated with a company."}, status=status.HTTP_400_BAD_REQUEST)

        # Get period from query params, default to 7days
        period = request.query_params.get('period', '7days')

        # Calculate the start date based on the period
        now = timezone.now()
        period_map = {
            '7days': timedelta(days=7),
            '30days': timedelta(days=30),
            '90days': timedelta(days=90),
            '1year': timedelta(days=365),
        }

        time_delta = period_map.get(period, timedelta(days=7))
        start_date = now - time_delta

        # Dictionary to aggregate sales by date
        sales_by_date = defaultdict(lambda: {'total_sales': 0, 'order_count': 0})

        # Get sales data from Sale model (completed sales)
        sale_data = Sale.objects.filter(
            company=company,
            status='completed',
            created_at__gte=start_date
        ).extra(
            select={'date': 'DATE(created_at)'}
        ).values('date').annotate(
            total_sales=Sum('total_amount'),
            order_count=Count('id')
        ).order_by('date')

        for item in sale_data:
            date_str = str(item['date'])
            sales_by_date[date_str]['total_sales'] += float(item['total_sales'] or 0)
            sales_by_date[date_str]['order_count'] += item['order_count']

        # Get sales data from Invoice model (paid invoices)
        invoice_data = Invoice.objects.filter(
            company=company,
            status='PAID',
            updated_at__gte=start_date  # Use updated_at as proxy for when it was marked paid
        ).extra(
            select={'date': 'DATE(updated_at)'}
        ).values('date').annotate(
            total_sales=Sum('total_amount'),
            order_count=Count('id')
        ).order_by('date')

        for item in invoice_data:
            date_str = str(item['date'])
            sales_by_date[date_str]['total_sales'] += float(item['total_sales'] or 0)
            sales_by_date[date_str]['order_count'] += item['order_count']

        # Generate all dates in the period to show zero values for days with no sales
        all_dates = []
        current_date = start_date.date()
        end_date = now.date()

        while current_date <= end_date:
            date_str = str(current_date)
            all_dates.append({
                "date": date_str,
                "sales": sales_by_date[date_str]['total_sales'],
                "order_count": sales_by_date[date_str]['order_count'],
            })
            current_date += dt_timedelta(days=1)

        # Format dates for display
        formatted_data = []
        for item in all_dates:
            date_obj = datetime.strptime(item['date'], '%Y-%m-%d')
            formatted_data.append({
                "date": date_obj.strftime('%b %d'),  # Format as "Jan 01"
                "sales": item['sales'],
                "order_count": item['order_count'],
            })

        return Response(formatted_data, status=status.HTTP_200_OK)
