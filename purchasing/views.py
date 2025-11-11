from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from rest_framework.response import Response
from django.http import HttpResponse
from django.db.models import Sum, Count, Q, F
from django.db import transaction
from datetime import datetime, date
from .models import Supplier, PurchaseOrder, PurchaseOrderLineItem
from .serializers import (
    SupplierSerializer,
    PurchaseOrderListSerializer,
    PurchaseOrderDetailSerializer
)
from .pdf_generator import generate_purchase_order_pdf
from .email_service import send_purchase_order_email
from decimal import Decimal


class SupplierViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing suppliers.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    serializer_class = SupplierSerializer

    def get_queryset(self):
        company = self.request.user.company
        queryset = Supplier.objects.filter(company=company)

        # Apply filters
        is_active = self.request.query_params.get('is_active')
        search = self.request.query_params.get('search')

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(contact_person__icontains=search) |
                Q(email__icontains=search)
            )

        return queryset.order_by('name')


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing purchase orders.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        company = self.request.user.company
        queryset = PurchaseOrder.objects.filter(company=company).select_related(
            'supplier', 'receiving_location', 'created_by'
        )

        # Apply filters
        supplier_id = self.request.query_params.get('supplier')
        status_filter = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if search:
            queryset = queryset.filter(
                Q(po_number__icontains=search) |
                Q(supplier__name__icontains=search)
            )

        if start_date:
            queryset = queryset.filter(order_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(order_date__lte=end_date)

        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return PurchaseOrderListSerializer
        return PurchaseOrderDetailSerializer

    def perform_create(self, serializer):
        company = self.request.user.company

        # Get tax rate from company settings if available
        tax_rate = getattr(company, 'purchase_tax_rate', Decimal('0.00'))

        # Generate PO number with retry logic
        max_retries = 5
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    last_po = PurchaseOrder.objects.filter(
                        company=company
                    ).select_for_update().order_by('-id').first()

                    if last_po and last_po.po_number:
                        try:
                            last_number = int(last_po.po_number.split('-')[-1])
                            new_number = last_number + 1
                        except (ValueError, IndexError):
                            new_number = 1
                    else:
                        new_number = 1

                    po_number = f"PO-{new_number:05d}"

                    serializer.save(
                        company=company,
                        created_by=self.request.user,
                        po_number=po_number,
                        tax_rate=tax_rate
                    )
                    break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                import time
                time.sleep(0.1)

    @action(detail=True, methods=['post'])
    def receive_items(self, request, pk=None):
        """
        Mark items as received and update quantities.
        Expected payload: { "line_items": [{ "id": 1, "quantity_received": 50 }, ...] }
        """
        purchase_order = self.get_object()

        if purchase_order.status == 'RECEIVED':
            return Response(
                {"error": "This purchase order has already been fully received"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if purchase_order.status == 'CANCELLED':
            return Response(
                {"error": "Cannot receive items for a cancelled purchase order"},
                status=status.HTTP_400_BAD_REQUEST
            )

        line_items_data = request.data.get('line_items', [])

        if not line_items_data:
            return Response(
                {"error": "No line items provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                for item_data in line_items_data:
                    line_item_id = item_data.get('id')
                    quantity_received = item_data.get('quantity_received', 0)

                    try:
                        line_item = purchase_order.line_items.get(id=line_item_id)
                        line_item.quantity_received = quantity_received
                        line_item.save()
                    except PurchaseOrderLineItem.DoesNotExist:
                        continue

                # Check if all items are fully received
                all_line_items = purchase_order.line_items.all()
                all_received = all(
                    item.quantity_received >= item.quantity_ordered
                    for item in all_line_items
                )
                some_received = any(
                    item.quantity_received > 0
                    for item in all_line_items
                )

                # Update PO status
                if all_received:
                    purchase_order.status = 'RECEIVED'
                    purchase_order.received_date = date.today()
                elif some_received:
                    purchase_order.status = 'PARTIALLY_RECEIVED'
                else:
                    purchase_order.status = 'CONFIRMED'

                purchase_order.save()

            serializer = self.get_serializer(purchase_order)
            return Response(serializer.data)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def add_to_inventory(self, request, pk=None):
        """
        Add received items to inventory at the receiving location.
        Only works if status is RECEIVED.
        """
        purchase_order = self.get_object()

        result = purchase_order.add_stock_to_inventory()

        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(purchase_order)
        return Response({
            "message": "Stock added to inventory successfully",
            "purchase_order": serializer.data
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel a purchase order.
        """
        purchase_order = self.get_object()

        if purchase_order.status in ['RECEIVED', 'PARTIALLY_RECEIVED']:
            return Response(
                {"error": "Cannot cancel a purchase order that has items received"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if purchase_order.stock_added:
            return Response(
                {"error": "Cannot cancel a purchase order with stock already added"},
                status=status.HTTP_400_BAD_REQUEST
            )

        purchase_order.status = 'CANCELLED'
        purchase_order.save()

        serializer = self.get_serializer(purchase_order)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get statistics about purchase orders.
        """
        company = request.user.company
        queryset = PurchaseOrder.objects.filter(company=company)

        # Count by status
        stats = {
            'total_pos': queryset.count(),
            'draft_pos': queryset.filter(status='DRAFT').count(),
            'sent_pos': queryset.filter(status='SENT').count(),
            'confirmed_pos': queryset.filter(status='CONFIRMED').count(),
            'partially_received_pos': queryset.filter(status='PARTIALLY_RECEIVED').count(),
            'received_pos': queryset.filter(status='RECEIVED').count(),
            'cancelled_pos': queryset.filter(status='CANCELLED').count(),
        }

        # Calculate total amounts
        total_value = queryset.filter(
            status__in=['SENT', 'CONFIRMED', 'PARTIALLY_RECEIVED', 'RECEIVED']
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        stats['total_value'] = float(total_value)

        # Pending POs (not yet received)
        pending_pos = queryset.filter(
            status__in=['SENT', 'CONFIRMED', 'PARTIALLY_RECEIVED']
        )
        stats['pending_pos_count'] = pending_pos.count()
        stats['pending_pos_value'] = float(
            pending_pos.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        )

        return Response(stats)

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """
        Download purchase order as PDF with company branding.
        Query params:
        - template: 'default', 'modern', 'classic' (optional)
        """
        purchase_order = self.get_object()
        template = request.query_params.get('template', 'default')

        try:
            # Generate PDF with specified template
            pdf_data = generate_purchase_order_pdf(purchase_order, template=template)

            # Create HTTP response with PDF
            response = HttpResponse(pdf_data, content_type='application/pdf')
            filename = f'PO-{purchase_order.po_number}.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            return response

        except Exception as e:
            return Response(
                {"error": f"Failed to generate PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def preview_pdf(self, request, pk=None):
        """
        Preview purchase order PDF in browser (inline display).
        Query params:
        - template: 'default', 'modern', 'classic' (optional)
        """
        purchase_order = self.get_object()
        template = request.query_params.get('template', 'default')

        try:
            # Generate PDF
            pdf_data = generate_purchase_order_pdf(purchase_order, template=template)

            # Create HTTP response with PDF for inline display
            response = HttpResponse(pdf_data, content_type='application/pdf')
            filename = f'PO-{purchase_order.po_number}.pdf'
            response['Content-Disposition'] = f'inline; filename="{filename}"'

            return response

        except Exception as e:
            return Response(
                {"error": f"Failed to generate PDF preview: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def send_to_supplier(self, request, pk=None):
        """
        Send purchase order to supplier via email with PDF attachment.
        Body params:
        - email: Optional email override (uses supplier email by default)
        """
        purchase_order = self.get_object()

        # Get optional email override
        recipient_email = request.data.get('email')

        try:
            # Send email
            result = send_purchase_order_email(purchase_order, recipient_email)

            if result['success']:
                # Update PO status to SENT if it was DRAFT
                if purchase_order.status == 'DRAFT':
                    purchase_order.status = 'SENT'
                    purchase_order.save()

                return Response({
                    'message': result['message'],
                    'status': purchase_order.status
                })
            else:
                return Response(
                    {"error": result['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            return Response(
                {"error": f"Failed to send email: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
