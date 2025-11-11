from rest_framework import generics, viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from django.db.models import Sum, Case, When, Value, CharField, F, Q, Count, Max, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from .models import Location, Category, Product, Client, Stock
from rest_framework.parsers import MultiPartParser
from .serializers import (
    LocationSerializer, CategorySerializer, ProductSerializer,
    ClientSerializer, StockSerializer, StockLevelDetailSerializer,
    StockAdjustmentSerializer, StockTransferSerializer
)
from rest_framework.views import APIView
from rest_framework.response import Response
from .tasks import process_product_import
from auditing.models import LogEntry
from django.db import transaction

class LocationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing locations with usage count.
    """
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return Location.objects.filter(company=self.request.user.company).annotate(
            usage_count=Count('stock_levels', distinct=True)
        ).order_by('name')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    def perform_update(self, serializer):
        # Ensure the location belongs to the user's company
        if serializer.instance.company != self.request.user.company:
            raise PermissionError("You don't have permission to update this location")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Check if location is in use
        usage_count = Stock.objects.filter(location=instance).count()
        if usage_count > 0:
            return Response(
                {"error": f"Cannot delete location. It is currently used by {usage_count} stock records."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)

class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing categories with usage count.
    """
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return Category.objects.filter(company=self.request.user.company).annotate(
            usage_count=Count('products', distinct=True)
        ).order_by('name')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    def perform_update(self, serializer):
        # Ensure the category belongs to the user's company
        if serializer.instance.company != self.request.user.company:
            raise PermissionError("You don't have permission to update this category")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Check if category is in use
        usage_count = Product.objects.filter(category=instance).count()
        if usage_count > 0:
            return Response(
                {"error": f"Cannot delete category. It is currently assigned to {usage_count} products."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)

class ProductViewSet(viewsets.ModelViewSet):
    """
    A full ViewSet for viewing and editing Product instances.
    This replaces ProductListCreateView to add support for updates and deletes.
    """
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    
    def get_queryset(self):
        company = self.request.user.company
        return Product.objects.filter(company=company).annotate(
            total_quantity=Sum('stock_levels__quantity', default=0),
            stock_status=Case(
                When(total_quantity=0, then=Value('Out of Stock')),
                When(total_quantity__lte=F('reorder_threshold'), then=Value('Low Stock')),
                default=Value('In Stock'),
                output_field=CharField()
            )
        ).order_by('name')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

class StockViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing stock levels.
    """
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return Stock.objects.filter(product__company=self.request.user.company)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data.get('product')
        location = serializer.validated_data.get('location')
        quantity = serializer.validated_data.get('quantity')

        if product.company != request.user.company or location.company != request.user.company:
            return Response({"error": "Invalid product or location."}, status=status.HTTP_403_FORBIDDEN)
        
        stock, created = Stock.objects.update_or_create(
            product=product,
            location=location,
            defaults={'quantity': quantity}
        )
        return Response(StockSerializer(stock).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
class ClientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing clients with CRM insights.
    Provides calculated fields: lifetime_value, amount_outstanding, last_activity.
    """
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        """
        Get clients with annotated CRM metrics:
        - lifetime_value: Sum of all paid invoices
        - amount_outstanding: Sum of unpaid/partially paid invoice balances
        - last_activity: Most recent quote or invoice date
        - total_quotes: Count of all quotes
        - total_invoices: Count of all invoices
        """
        queryset = Client.objects.filter(company=self.request.user.company)

        # Annotate with calculated fields
        queryset = queryset.annotate(
            # Lifetime Value: Sum of all PAID invoice totals
            lifetime_value=Coalesce(
                Sum(
                    'invoices__total_amount',
                    filter=Q(invoices__status='PAID')
                ),
                Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),

            # Amount Outstanding: Sum of (total - paid) for UNPAID, OVERDUE, and PARTIALLY_PAID invoices
            amount_outstanding=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F('invoices__total_amount') - F('invoices__amount_paid'),
                        output_field=DecimalField(max_digits=10, decimal_places=2)
                    ),
                    filter=Q(invoices__status__in=['UNPAID', 'OVERDUE', 'PARTIALLY_PAID'])
                ),
                Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),

            # Last Activity: Most recent quote or invoice date
            last_quote_date=Max('quotes__date_issued'),
            last_invoice_date=Max('invoices__issue_date'),

            # Counts
            total_quotes=Count('quotes', distinct=True),
            total_invoices=Count('invoices', distinct=True)
        )

        return queryset.order_by('name')

    def list(self, request, *args, **kwargs):
        """Override list to add last_activity field to each client"""
        queryset = self.filter_queryset(self.get_queryset())

        # Post-process to add last_activity
        clients = list(queryset)
        for client in clients:
            dates = [d for d in [client.last_quote_date, client.last_invoice_date] if d is not None]
            client.last_activity = max(dates) if dates else None

        serializer = self.get_serializer(clients, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to add last_activity field"""
        instance = self.get_object()

        # Add last_activity field
        dates = [d for d in [instance.last_quote_date, instance.last_invoice_date] if d is not None]
        instance.last_activity = max(dates) if dates else None

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    def perform_update(self, serializer):
        # Ensure the client belongs to the user's company
        if serializer.instance.company != self.request.user.company:
            raise PermissionError("You don't have permission to update this client")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Check if client has any quotes or invoices
        quote_count = instance.quotes.count()
        invoice_count = instance.invoices.count()

        if quote_count > 0 or invoice_count > 0:
            return Response(
                {
                    "error": f"Cannot delete client. They have {quote_count} quote(s) and {invoice_count} invoice(s)."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)


class DashboardStatsView(APIView):
    """
    Provides a collection of statistics for the main dashboard.
    This is a read-only endpoint.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request, *args, **kwargs):
        company = request.user.company
        if not company:
            return Response({"error": "User is not associated with a company."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Get Key Performance Indicators (KPIs)
        total_products = Product.objects.filter(company=company).count()
        total_clients = Client.objects.filter(company=company).count()
        
        # Calculate the total value of all stock
        # This requires a more complex query joining Stock and Product tables.
        # For now, we will get the total quantity of items.
        total_stock_quantity = Stock.objects.filter(product__company=company).aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0

        # 2. Get a list of low-stock items (e.g., quantity <= 10)
        low_stock_items = Stock.objects.filter(product__company=company, quantity__lte=10).select_related('product', 'location')
        low_stock_data = [
            {
                "product_name": item.product.name,
                "location_name": item.location.name,
                "quantity": item.quantity,
                "sku": item.product.sku
            }
            for item in low_stock_items
        ]

        # 3. Get recent activity (using our audit log)
        # This would require importing the LogEntry model, which we'll do in a later step.

        # Consolidate all stats into a single response object
        stats = {
            "kpis": {
                "total_products": total_products,
                "total_clients": total_clients,
                "total_stock_quantity": total_stock_quantity,
                "total_stock_value": 0, # Placeholder for a future calculation
            },
            "low_stock_items": low_stock_data,
            "recent_activity": [] # Placeholder for audit logs
        }
        
        return Response(stats, status=status.HTTP_200_OK)
    
class ProductBulkImportView(APIView):
    """
    Accepts a CSV file for bulk product import and queues a background task.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    parser_classes = [MultiPartParser] # Handles file uploads (multipart/form-data)

    def post(self, request, *args, **kwargs):
        csv_file = request.FILES.get('csv_file')

        if not csv_file:
            return Response({"error": "No CSV file provided."}, status=status.HTTP_400_BAD_REQUEST)

        if not csv_file.name.endswith('.csv'):
            return Response({"error": "Please upload a valid .csv file."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Read the file's content into a string to pass to Celery
            csv_content = csv_file.read().decode('utf-8')
            company_id = request.user.company.id

            # 2. Trigger the Celery task to process the file in the background
            process_product_import.delay(csv_content, company_id)

            # 3. Return a 202 Accepted response to the user immediately
            return Response(
                {"status": "Your file is being processed. The new products will appear in your inventory shortly."},
                status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response({"error": f"An error occurred while processing the file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StockControlOverviewView(APIView):
    """
    Provides a detailed overview of all stock levels with filtering capabilities.
    Supports filtering by location, category, and product search.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request, *args, **kwargs):
        company = request.user.company
        if not company:
            return Response({"error": "User is not associated with a company."}, status=status.HTTP_400_BAD_REQUEST)

        # Get all stock levels for this company
        stock_queryset = Stock.objects.filter(product__company=company).select_related('product', 'location')

        # Apply filters
        location_id = request.query_params.get('location')
        category_id = request.query_params.get('category')
        search = request.query_params.get('search')

        if location_id:
            stock_queryset = stock_queryset.filter(location_id=location_id)

        if category_id:
            stock_queryset = stock_queryset.filter(product__category_id=category_id)

        if search:
            stock_queryset = stock_queryset.filter(
                Q(product__name__icontains=search) | Q(product__sku__icontains=search)
            )

        # Order by product name
        stock_queryset = stock_queryset.order_by('product__name', 'location__name')

        # Serialize the data
        serializer = StockLevelDetailSerializer(stock_queryset, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class StockAdjustmentView(APIView):
    """
    Handles stock adjustments (add, remove, set quantity).
    Creates audit log entries for all adjustments.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        company = request.user.company
        if not company:
            return Response({"error": "User is not associated with a company."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = StockAdjustmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        product = validated_data['product_obj']
        location = validated_data['location_obj']
        action = validated_data['action']
        quantity = validated_data['quantity']
        reason = validated_data['reason']

        # Verify product and location belong to the user's company
        if product.company != company or location.company != company:
            return Response({"error": "Invalid product or location."}, status=status.HTTP_403_FORBIDDEN)

        # Get or create the stock record
        stock, created = Stock.objects.get_or_create(
            product=product,
            location=location,
            defaults={'quantity': 0}
        )

        # Store the old quantity for audit logging
        old_quantity = stock.quantity

        # Perform the adjustment
        if action == 'add':
            stock.quantity += quantity
            action_type = 'STOCK_ADDED'
        elif action == 'remove':
            if stock.quantity < quantity:
                return Response(
                    {"error": f"Insufficient stock. Available: {stock.quantity}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            stock.quantity -= quantity
            action_type = 'STOCK_REMOVED'
        elif action == 'set':
            stock.quantity = quantity
            action_type = 'STOCK_SET'

        stock.save()

        # Create audit log entry
        LogEntry.objects.create(
            user=request.user,
            company=company,
            action_type=action_type,
            details={
                'product_id': product.id,
                'product_name': product.name,
                'product_sku': product.sku,
                'location_id': location.id,
                'location_name': location.name,
                'old_quantity': old_quantity,
                'new_quantity': stock.quantity,
                'quantity_changed': quantity,
                'action': action,
                'reason': reason
            }
        )

        # Return the updated stock information
        return Response(
            StockLevelDetailSerializer(stock).data,
            status=status.HTTP_200_OK
        )


class StockTransferView(APIView):
    """
    Handles stock transfers between locations.
    Creates audit log entries for all transfers.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        company = request.user.company
        if not company:
            return Response({"error": "User is not associated with a company."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = StockTransferSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        product = validated_data['product_obj']
        from_location = validated_data['from_location_obj']
        to_location = validated_data['to_location_obj']
        quantity = validated_data['quantity']
        reason = validated_data['reason']
        source_stock = validated_data['source_stock_obj']

        # Verify locations belong to the user's company
        if from_location.company != company or to_location.company != company:
            return Response({"error": "Invalid locations."}, status=status.HTTP_403_FORBIDDEN)

        # Reduce stock at source location
        old_source_quantity = source_stock.quantity
        source_stock.quantity -= quantity
        source_stock.save()

        # Increase stock at destination location
        dest_stock, dest_created = Stock.objects.get_or_create(
            product=product,
            location=to_location,
            defaults={'quantity': 0}
        )
        old_dest_quantity = dest_stock.quantity
        dest_stock.quantity += quantity
        dest_stock.save()

        # Create audit log entry
        LogEntry.objects.create(
            user=request.user,
            company=company,
            action_type='STOCK_TRANSFERRED',
            details={
                'product_id': product.id,
                'product_name': product.name,
                'product_sku': product.sku,
                'from_location_id': from_location.id,
                'from_location_name': from_location.name,
                'to_location_id': to_location.id,
                'to_location_name': to_location.name,
                'quantity_transferred': quantity,
                'from_old_quantity': old_source_quantity,
                'from_new_quantity': source_stock.quantity,
                'to_old_quantity': old_dest_quantity,
                'to_new_quantity': dest_stock.quantity,
                'reason': reason
            }
        )

        # Return both updated stock records
        return Response({
            'source_stock': StockLevelDetailSerializer(source_stock).data,
            'destination_stock': StockLevelDetailSerializer(dest_stock).data,
            'message': f'Successfully transferred {quantity} units from {from_location.name} to {to_location.name}'
        }, status=status.HTTP_200_OK)


class StockHistoryView(APIView):
    """
    Retrieves the audit trail for a specific product at a specific location.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request, *args, **kwargs):
        company = request.user.company
        if not company:
            return Response({"error": "User is not associated with a company."}, status=status.HTTP_400_BAD_REQUEST)

        product_id = request.query_params.get('product')
        location_id = request.query_params.get('location')

        if not product_id:
            return Response({"error": "Product ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Verify the product belongs to the user's company
        try:
            product = Product.objects.get(id=product_id, company=company)
        except Product.DoesNotExist:
            return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        # Build the filter for log entries
        log_filter = Q(company=company, details__product_id=product_id)
        log_filter &= Q(
            action_type__in=[
                'STOCK_ADDED', 'STOCK_REMOVED', 'STOCK_SET',
                'STOCK_TRANSFERRED', 'STOCK_LEVEL_ADJUSTED'
            ]
        )

        # If location is specified, filter by location
        if location_id:
            log_filter &= (
                Q(details__location_id=location_id) |
                Q(details__from_location_id=location_id) |
                Q(details__to_location_id=location_id)
            )

        # Get the log entries
        log_entries = LogEntry.objects.filter(log_filter).order_by('-timestamp')

        # Format the response
        history_data = []
        for entry in log_entries:
            history_data.append({
                'id': entry.id,
                'timestamp': entry.timestamp,
                'user': entry.user.email if entry.user else 'System',
                'action_type': entry.get_action_type_display(),
                'action_type_code': entry.action_type,
                'details': entry.details
            })

        return Response({
            'product_id': product.id,
            'product_name': product.name,
            'product_sku': product.sku,
            'history': history_data
        }, status=status.HTTP_200_OK)


