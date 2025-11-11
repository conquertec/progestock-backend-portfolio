from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from rest_framework import status
from django.db.models import Sum, Count, Avg, F, Q, ExpressionWrapper, DecimalField, Case, When, Value
from django.db.models.functions import TruncDate, TruncMonth, Coalesce, ExtractYear, ExtractMonth
from datetime import datetime, timedelta
from decimal import Decimal
from inventory.models import Product, Stock
from sales.models import Invoice, InvoiceLineItem, Quote


class SalesReportView(APIView):
    """
    Comprehensive Sales Report with Revenue, Profit, and Best Sellers.
    Supports date range filtering and provides detailed analytics.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        company = request.user.company
        if not company:
            return Response(
                {"error": "User is not associated with a company."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse date range parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # Default to last 30 days if not provided
        if not end_date:
            end_date = datetime.now().date()
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        if not start_date:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

        # Filter invoices by company and date range
        invoices = Invoice.objects.filter(
            company=company,
            issue_date__gte=start_date,
            issue_date__lte=end_date
        )

        # KPI Calculations
        total_revenue = invoices.filter(status='PAID').aggregate(
            total=Coalesce(Sum('total_amount'), Value(0), output_field=DecimalField())
        )['total']

        total_invoices = invoices.count()

        avg_invoice_value = invoices.aggregate(
            avg=Coalesce(Avg('total_amount'), Value(0), output_field=DecimalField())
        )['avg']

        # Calculate profit from line items
        # Profit = (selling_price - purchase_price) * quantity
        line_items = InvoiceLineItem.objects.filter(
            invoice__in=invoices.filter(status='PAID')
        ).select_related('product')

        total_profit = Decimal('0.00')
        for item in line_items:
            if item.product:
                profit_per_unit = item.unit_price - item.product.purchase_price
                total_profit += profit_per_unit * item.quantity

        # Revenue over time (daily for date ranges <= 90 days, monthly otherwise)
        days_diff = (end_date - start_date).days

        # Use simpler approach compatible with SQLite
        if days_diff <= 90:
            # Daily grouping - use issue_date directly
            revenue_over_time = invoices.filter(status='PAID').values(
                'issue_date'
            ).annotate(
                revenue=Sum('total_amount')
            ).order_by('issue_date')
        else:
            # Monthly grouping - manual grouping for SQLite compatibility
            revenue_over_time = invoices.filter(status='PAID').annotate(
                year=ExtractYear('issue_date'),
                month=ExtractMonth('issue_date')
            ).values('year', 'month').annotate(
                revenue=Sum('total_amount')
            ).order_by('year', 'month')

        # Top Products by Revenue
        top_products = InvoiceLineItem.objects.filter(
            invoice__in=invoices.filter(status='PAID')
        ).values('product__name', 'product__sku').annotate(
            total_revenue=Sum(F('quantity') * F('unit_price')),
            total_quantity=Sum('quantity')
        ).order_by('-total_revenue')[:10]

        # Top Clients by Revenue
        top_clients = invoices.filter(status='PAID').values(
            'client__name', 'client__id'
        ).annotate(
            total_revenue=Sum('total_amount'),
            invoice_count=Count('id')
        ).order_by('-total_revenue')[:10]

        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days_diff
            },
            'kpis': {
                'total_revenue': float(total_revenue),
                'total_profit': float(total_profit),
                'total_invoices': total_invoices,
                'average_invoice_value': float(avg_invoice_value),
                'profit_margin': float((total_profit / total_revenue * 100) if total_revenue > 0 else 0)
            },
            'revenue_over_time': [
                {
                    'date': (
                        item['issue_date'].isoformat() if 'issue_date' in item
                        else f"{item['year']}-{item['month']:02d}-01"
                    ),
                    'revenue': float(item['revenue'] or 0)
                }
                for item in revenue_over_time
            ],
            'top_products': [
                {
                    'name': item['product__name'],
                    'sku': item['product__sku'],
                    'revenue': float(item['total_revenue']),
                    'quantity': item['total_quantity']
                }
                for item in top_products
            ],
            'top_clients': [
                {
                    'id': item['client__id'],
                    'name': item['client__name'],
                    'revenue': float(item['total_revenue']),
                    'invoice_count': item['invoice_count']
                }
                for item in top_clients
            ]
        }, status=status.HTTP_200_OK)


class InventoryValuationView(APIView):
    """
    Inventory Valuation Report for accounting and asset tracking.
    Calculates total inventory value based on purchase prices.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        company = request.user.company
        if not company:
            return Response(
                {"error": "User is not associated with a company."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse filter parameters
        location_id = request.query_params.get('location')
        category_id = request.query_params.get('category')

        # Get all stock for this company
        stock_queryset = Stock.objects.filter(
            product__company=company
        ).select_related('product', 'location', 'product__category')

        # Apply filters
        if location_id:
            stock_queryset = stock_queryset.filter(location_id=location_id)

        if category_id:
            stock_queryset = stock_queryset.filter(product__category_id=category_id)

        # Calculate totals
        total_quantity = stock_queryset.aggregate(
            total=Coalesce(Sum('quantity'), Value(0))
        )['total']

        # Calculate total inventory value (quantity * purchase_price)
        total_value = Decimal('0.00')
        inventory_items = []

        for stock in stock_queryset:
            item_value = stock.quantity * stock.product.purchase_price
            total_value += item_value

            inventory_items.append({
                'product_id': stock.product.id,
                'product_name': stock.product.name,
                'sku': stock.product.sku,
                'category': stock.product.category.name if stock.product.category else None,
                'location': stock.location.name,
                'purchase_price': float(stock.product.purchase_price),
                'selling_price': float(stock.product.price),
                'quantity': stock.quantity,
                'total_value': float(item_value)
            })

        # Sort by total value descending
        inventory_items.sort(key=lambda x: x['total_value'], reverse=True)

        return Response({
            'kpis': {
                'total_quantity': total_quantity,
                'total_inventory_value': float(total_value),
                'unique_products': len(inventory_items)
            },
            'inventory_items': inventory_items
        }, status=status.HTTP_200_OK)


class QuoteConversionView(APIView):
    """
    Quote Conversion Report to measure sales effectiveness.
    Tracks conversion rates and time to acceptance.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        company = request.user.company
        if not company:
            return Response(
                {"error": "User is not associated with a company."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse date range parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # Default to last 30 days if not provided
        if not end_date:
            end_date = datetime.now().date()
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        if not start_date:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

        # Filter quotes by company and date range
        quotes = Quote.objects.filter(
            company=company,
            date_issued__gte=start_date,
            date_issued__lte=end_date
        )

        # Count by status
        total_quotes = quotes.count()
        status_breakdown = quotes.values('status').annotate(
            count=Count('id')
        )

        status_counts = {item['status']: item['count'] for item in status_breakdown}

        quotes_sent = status_counts.get('SENT', 0) + status_counts.get('ACCEPTED', 0) + status_counts.get('REJECTED', 0) + status_counts.get('INVOICED', 0)
        quotes_accepted = status_counts.get('ACCEPTED', 0) + status_counts.get('INVOICED', 0)
        quotes_rejected = status_counts.get('REJECTED', 0)
        quotes_draft = status_counts.get('DRAFT', 0)

        # Calculate conversion rate
        conversion_rate = (quotes_accepted / quotes_sent * 100) if quotes_sent > 0 else 0

        # Calculate average time to acceptance (simplified - would need additional date tracking)
        # For now, we'll use a placeholder
        avg_time_to_acceptance = 0  # Days - would require tracking acceptance_date

        # Status breakdown for pie chart
        status_distribution = [
            {'status': 'Accepted', 'count': status_counts.get('ACCEPTED', 0) + status_counts.get('INVOICED', 0)},
            {'status': 'Rejected', 'count': status_counts.get('REJECTED', 0)},
            {'status': 'Sent (Pending)', 'count': status_counts.get('SENT', 0)},
            {'status': 'Draft', 'count': status_counts.get('DRAFT', 0)},
        ]

        # Top performing clients by acceptance rate
        client_performance = quotes.exclude(status='DRAFT').values(
            'client__id', 'client__name'
        ).annotate(
            total_quotes=Count('id'),
            accepted_quotes=Count('id', filter=Q(status__in=['ACCEPTED', 'INVOICED'])),
            total_value=Sum('total_amount')
        ).order_by('-accepted_quotes')[:10]

        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'kpis': {
                'total_quotes': total_quotes,
                'quotes_sent': quotes_sent,
                'quotes_accepted': quotes_accepted,
                'quotes_rejected': quotes_rejected,
                'conversion_rate': round(conversion_rate, 2),
                'avg_time_to_acceptance': avg_time_to_acceptance
            },
            'status_distribution': status_distribution,
            'client_performance': [
                {
                    'client_id': item['client__id'],
                    'client_name': item['client__name'],
                    'total_quotes': item['total_quotes'],
                    'accepted_quotes': item['accepted_quotes'],
                    'conversion_rate': round((item['accepted_quotes'] / item['total_quotes'] * 100) if item['total_quotes'] > 0 else 0, 2),
                    'total_value': float(item['total_value'] or 0)
                }
                for item in client_performance
            ]
        }, status=status.HTTP_200_OK)
