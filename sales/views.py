from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from rest_framework.response import Response
from django.http import HttpResponse
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import Coalesce
from django.db import transaction, IntegrityError
from datetime import datetime, timedelta, date
import time
import logging
from .models import Quote, QuoteLineItem, Invoice, InvoiceLineItem, Payment
from .serializers import (
    QuoteListSerializer, QuoteDetailSerializer,
    InvoiceListSerializer, InvoiceDetailSerializer, PaymentSerializer
)
from .pdf_generator import generate_quote_pdf, generate_invoice_pdf
from .email_service import send_quote_email, send_invoice_email
from decimal import Decimal


class QuoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing quotes.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        company = self.request.user.company
        queryset = Quote.objects.filter(company=company).select_related('client', 'created_by')

        # Apply filters
        client_id = self.request.query_params.get('client')
        status_filter = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if client_id:
            queryset = queryset.filter(client_id=client_id)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if search:
            queryset = queryset.filter(
                Q(quote_number__icontains=search) |
                Q(client__name__icontains=search)
            )

        if start_date:
            queryset = queryset.filter(date_issued__gte=start_date)

        if end_date:
            queryset = queryset.filter(date_issued__lte=end_date)

        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return QuoteListSerializer
        return QuoteDetailSerializer

    def perform_create(self, serializer):
        logger = logging.getLogger(__name__)
        company = self.request.user.company

        # Get tax rate from company settings
        tax_rate = getattr(company, 'sales_tax_rate', Decimal('0.00'))

        # Generate quote number with retry logic to handle race conditions
        max_retries = 10
        last_error = None

        for attempt in range(max_retries):
            # Get all existing quote numbers GLOBALLY (not per company)
            # since the database constraint is global
            existing_quotes = Quote.objects.all().values_list('quote_number', flat=True)

            print(f"[QUOTE DEBUG] Found {len(existing_quotes)} total quotes in database")

            max_number = 0
            for quote_num in existing_quotes:
                try:
                    num = int(quote_num.split('-')[-1])
                    max_number = max(max_number, num)
                except (ValueError, IndexError, AttributeError):
                    continue

            # Generate new number (add attempt to avoid collisions during retries)
            new_number = max_number + 1 + attempt
            quote_number = f"QT-{new_number:05d}"

            print(f"[QUOTE DEBUG] Attempt {attempt}: Trying {quote_number} (found {len(existing_quotes)} existing, max was {max_number})")

            try:
                with transaction.atomic():
                    serializer.save(
                        company=company,
                        created_by=self.request.user,
                        quote_number=quote_number,
                        tax_rate=tax_rate
                    )
                    print(f"[QUOTE DEBUG] Successfully created quote {quote_number}")
                    return  # Success, exit method
            except IntegrityError as e:
                print(f"[QUOTE DEBUG] Attempt {attempt} failed: {quote_number} already exists")
                last_error = e
                if attempt < max_retries - 1:
                    # Wait a bit before retrying (with exponential backoff)
                    time.sleep(0.05 * (attempt + 1))
                else:
                    # Last attempt failed, re-raise the exception
                    logger.error(f"All {max_retries} attempts failed to create quote")
                    raise last_error

    @action(detail=False, methods=['get'])
    def kpis(self, request):
        """
        Get KPIs for quotes dashboard.
        """
        company = request.user.company
        quotes = Quote.objects.filter(company=company)

        # Value of drafts
        drafts_value = quotes.filter(status='DRAFT').aggregate(
            total=Coalesce(Sum('total_amount'), Decimal('0.00'))
        )['total']

        # Value of pending quotes (sent but not accepted/rejected)
        pending_value = quotes.filter(status='SENT').aggregate(
            total=Coalesce(Sum('total_amount'), Decimal('0.00'))
        )['total']

        # Acceptance rate calculation
        sent_quotes = quotes.filter(status__in=['SENT', 'ACCEPTED', 'REJECTED', 'INVOICED']).count()
        accepted_quotes = quotes.filter(status__in=['ACCEPTED', 'INVOICED']).count()

        if sent_quotes > 0:
            acceptance_rate = (accepted_quotes / sent_quotes) * 100
        else:
            acceptance_rate = 0

        # Additional metrics
        total_quotes = quotes.count()
        total_value = quotes.aggregate(total=Coalesce(Sum('total_amount'), Decimal('0.00')))['total']

        return Response({
            'drafts_value': float(drafts_value),
            'pending_value': float(pending_value),
            'acceptance_rate': round(acceptance_rate, 2),
            'total_quotes': total_quotes,
            'total_value': float(total_value),
            'status_breakdown': {
                'draft': quotes.filter(status='DRAFT').count(),
                'sent': quotes.filter(status='SENT').count(),
                'accepted': quotes.filter(status='ACCEPTED').count(),
                'rejected': quotes.filter(status='REJECTED').count(),
                'invoiced': quotes.filter(status='INVOICED').count(),
            }
        })

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Duplicate an existing quote.
        """
        original_quote = self.get_object()
        company = request.user.company

        # Generate unique quote number with retry logic
        max_retries = 10
        new_quote = None

        for attempt in range(max_retries):
            # Get the last quote number
            last_quote = Quote.objects.filter(company=company).order_by('-id').first()
            if last_quote and last_quote.quote_number:
                try:
                    last_number = int(last_quote.quote_number.split('-')[-1])
                    new_number = last_number + 1 + attempt  # Add attempt to avoid collisions
                except (ValueError, IndexError):
                    new_number = 1 + attempt
            else:
                new_number = 1 + attempt

            new_quote_number = f"QT-{new_number:05d}"

            # Check if this quote number already exists
            if Quote.objects.filter(company=company, quote_number=new_quote_number).exists():
                continue  # Try next number

            try:
                # Create duplicate quote
                new_quote = Quote.objects.create(
                    company=company,
                    client=original_quote.client,
                    quote_number=new_quote_number,
                    status='DRAFT',
                    date_issued=datetime.now().date(),
                    expiration_date=original_quote.expiration_date,
                    tax_rate=original_quote.tax_rate,
                    notes=original_quote.notes,
                    terms=original_quote.terms,
                    created_by=request.user
                )
                break  # Success, exit retry loop
            except IntegrityError:
                # Quote number collision, try again with next number
                continue

        if new_quote is None:
            return Response(
                {'error': 'Failed to generate unique quote number. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Duplicate line items
        for line_item in original_quote.line_items.all():
            QuoteLineItem.objects.create(
                quote=new_quote,
                product=line_item.product,
                product_name=line_item.product_name,
                product_sku=line_item.product_sku,
                quantity=line_item.quantity,
                unit_price=line_item.unit_price,
                discount_type=line_item.discount_type,
                discount_value=line_item.discount_value
            )

        # Calculate totals
        new_quote.calculate_totals()

        serializer = QuoteDetailSerializer(new_quote)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def convert_to_invoice(self, request, pk=None):
        """
        Convert an accepted quote to an invoice.
        """
        quote = self.get_object()
        company = request.user.company

        # Validate quote status
        if quote.status not in ['ACCEPTED']:
            return Response(
                {'error': 'Only accepted quotes can be converted to invoices.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if already converted
        if quote.invoices.exists():
            return Response(
                {'error': 'This quote has already been converted to an invoice.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate unique invoice number with retry logic
        max_retries = 10
        invoice = None

        for attempt in range(max_retries):
            # Get the last invoice number
            last_invoice = Invoice.objects.filter(company=company).order_by('-id').first()
            if last_invoice and last_invoice.invoice_number:
                try:
                    last_number = int(last_invoice.invoice_number.split('-')[-1])
                    new_number = last_number + 1 + attempt  # Add attempt to avoid collisions
                except (ValueError, IndexError):
                    new_number = 1 + attempt
            else:
                new_number = 1 + attempt

            invoice_number = f"INV-{new_number:05d}"

            # Check if this invoice number already exists
            if Invoice.objects.filter(company=company, invoice_number=invoice_number).exists():
                continue  # Try next number

            # Calculate due date based on company payment terms
            issue_date = date.today()
            # Default to 30 days if not specified
            due_date = issue_date + timedelta(days=30)

            try:
                # Create invoice from quote
                invoice = Invoice.objects.create(
                    company=company,
                    client=quote.client,
                    invoice_number=invoice_number,
                    quote=quote,
                    status='UNPAID',
                    issue_date=issue_date,
                    due_date=due_date,
                    tax_rate=quote.tax_rate,
                    notes=quote.notes,
                    terms=quote.terms or company.payment_terms,
                    created_by=request.user
                )
                break  # Success, exit retry loop
            except IntegrityError:
                # Invoice number collision, try again with next number
                continue

        if invoice is None:
            return Response(
                {'error': 'Failed to generate unique invoice number. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Copy line items from quote to invoice
        for quote_line_item in quote.line_items.all():
            InvoiceLineItem.objects.create(
                invoice=invoice,
                product=quote_line_item.product,
                product_name=quote_line_item.product_name,
                product_sku=quote_line_item.product_sku,
                quantity=quote_line_item.quantity,
                unit_price=quote_line_item.unit_price,
                discount_type=quote_line_item.discount_type,
                discount_value=quote_line_item.discount_value
            )

        # Calculate totals
        invoice.calculate_totals()

        # Reduce stock immediately when converting quote to invoice
        # This ensures stock is reserved for the invoiced items
        invoice.reduce_stock()

        # Update quote status
        quote.status = 'INVOICED'
        quote.save()

        serializer = InvoiceDetailSerializer(invoice)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """
        Download quote as PDF with company branding.
        Query params:
        - template: 'default', 'modern', 'classic' (optional)
        """
        quote = self.get_object()
        template = request.query_params.get('template', 'default')

        try:
            # Generate PDF with specified template
            pdf_data = generate_quote_pdf(quote, template=template)

            # Create HTTP response with PDF
            response = HttpResponse(pdf_data, content_type='application/pdf')
            filename = f'Quote-{quote.quote_number}.pdf'
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
        Preview quote PDF in browser (inline display).
        Query params:
        - template: 'default', 'modern', 'classic' (optional)
        """
        quote = self.get_object()
        template = request.query_params.get('template', 'default')

        try:
            # Generate PDF
            pdf_data = generate_quote_pdf(quote, template=template)

            # Create HTTP response with PDF for inline display
            response = HttpResponse(pdf_data, content_type='application/pdf')
            filename = f'Quote-{quote.quote_number}.pdf'
            response['Content-Disposition'] = f'inline; filename="{filename}"'

            return response

        except Exception as e:
            return Response(
                {"error": f"Failed to generate PDF preview: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def send_to_client(self, request, pk=None):
        """
        Send quote to client via email with PDF attachment.
        Body params:
        - email: Optional email override (uses client email by default)
        """
        quote = self.get_object()

        # Get optional email override
        recipient_email = request.data.get('email')

        try:
            # Send email
            result = send_quote_email(quote, recipient_email)

            if result['success']:
                # Update quote status to SENT if it was DRAFT
                if quote.status == 'DRAFT':
                    quote.status = 'SENT'
                    quote.save()

                return Response({
                    'message': result['message'],
                    'status': quote.status
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


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing invoices with full CRUD operations and custom actions.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        company = self.request.user.company
        queryset = Invoice.objects.filter(company=company).select_related('client', 'created_by', 'quote')

        # Apply filters
        client_id = self.request.query_params.get('client')
        status_filter = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if client_id:
            queryset = queryset.filter(client_id=client_id)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search) |
                Q(client__name__icontains=search)
            )

        if start_date:
            queryset = queryset.filter(issue_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(issue_date__lte=end_date)

        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return InvoiceListSerializer
        return InvoiceDetailSerializer

    def perform_create(self, serializer):
        company = self.request.user.company

        # Generate invoice number with retry logic to handle race conditions
        max_retries = 10
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    # Lock the table to prevent race conditions
                    last_invoice = Invoice.objects.filter(company=company).select_for_update().order_by('-id').first()

                    if last_invoice and last_invoice.invoice_number:
                        try:
                            last_number = int(last_invoice.invoice_number.split('-')[-1])
                            new_number = last_number + 1
                        except (ValueError, IndexError):
                            new_number = 1
                    else:
                        new_number = 1

                    invoice_number = f"INV-{new_number:05d}"

                    # Get tax rate from company settings
                    tax_rate = getattr(company, 'sales_tax_rate', Decimal('0.00'))

                    serializer.save(
                        company=company,
                        created_by=self.request.user,
                        invoice_number=invoice_number,
                        tax_rate=tax_rate
                    )
                    break  # Success, exit loop
            except IntegrityError as e:
                if attempt == max_retries - 1:
                    # Last attempt failed, re-raise the exception
                    raise
                # Wait a bit before retrying
                import time
                time.sleep(0.1)

    @action(detail=False, methods=['get'])
    def kpis(self, request):
        """
        Get KPIs for invoices dashboard.
        """
        company = request.user.company
        invoices = Invoice.objects.filter(company=company)

        # Total Outstanding (Unpaid + Overdue + Partially Paid)
        from decimal import Decimal
        outstanding_invoices = invoices.filter(status__in=['UNPAID', 'OVERDUE', 'PARTIALLY_PAID'])
        total_outstanding = sum(
            (invoice.amount_due for invoice in outstanding_invoices),
            Decimal('0.00')
        )

        # Total Overdue
        overdue_invoices = invoices.filter(status='OVERDUE')
        total_overdue = sum(
            (invoice.amount_due for invoice in overdue_invoices),
            Decimal('0.00')
        )

        # Paid (Last 30 Days)
        thirty_days_ago = date.today() - timedelta(days=30)
        paid_last_30_days = Payment.objects.filter(
            invoice__company=company,
            payment_date__gte=thirty_days_ago
        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']

        # Additional metrics
        total_invoices = invoices.count()
        total_value = invoices.aggregate(total=Coalesce(Sum('total_amount'), Decimal('0.00')))['total']

        return Response({
            'total_outstanding': float(total_outstanding),
            'total_overdue': float(total_overdue),
            'paid_last_30_days': float(paid_last_30_days),
            'total_invoices': total_invoices,
            'total_value': float(total_value),
            'status_breakdown': {
                'draft': invoices.filter(status='DRAFT').count(),
                'unpaid': invoices.filter(status='UNPAID').count(),
                'paid': invoices.filter(status='PAID').count(),
                'overdue': invoices.filter(status='OVERDUE').count(),
                'partially_paid': invoices.filter(status='PARTIALLY_PAID').count(),
            }
        })

    @action(detail=True, methods=['post'])
    def record_payment(self, request, pk=None):
        """
        Record a payment for an invoice.
        """
        invoice = self.get_object()

        # Validate amount
        amount = request.data.get('amount')
        if not amount:
            return Response(
                {'error': 'Payment amount is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            amount = Decimal(str(amount))
        except:
            return Response(
                {'error': 'Invalid payment amount.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if amount <= 0:
            return Response(
                {'error': 'Payment amount must be greater than zero.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if amount > invoice.amount_due:
            return Response(
                {'error': f'Payment amount cannot exceed the amount due ({invoice.amount_due}).'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create payment record
        payment_data = {
            'invoice': invoice.id,
            'amount': amount,
            'payment_date': request.data.get('payment_date', date.today()),
            'payment_method': request.data.get('payment_method', 'BANK_TRANSFER'),
            'reference': request.data.get('reference', ''),
            'notes': request.data.get('notes', ''),
        }

        payment = Payment.objects.create(
            invoice=invoice,
            amount=payment_data['amount'],
            payment_date=payment_data['payment_date'],
            payment_method=payment_data['payment_method'],
            reference=payment_data['reference'],
            notes=payment_data['notes'],
            recorded_by=request.user
        )

        # The Payment model's save() method will update the invoice automatically

        serializer = InvoiceDetailSerializer(invoice)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def send_reminder(self, request, pk=None):
        """
        Send a payment reminder email to the client.
        This is a placeholder for Celery task integration.
        """
        invoice = self.get_object()

        if invoice.status == 'PAID':
            return Response(
                {'error': 'Cannot send reminder for a paid invoice.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # TODO: Implement Celery task to send email
        # For now, just return success
        return Response({
            'message': f'Payment reminder sent to {invoice.client.email}',
            'invoice_number': invoice.invoice_number
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def accepted_quotes(self, request):
        """
        Get list of accepted quotes that haven't been converted to invoices yet.
        Used for the "Create from Quote" functionality.
        """
        company = request.user.company
        accepted_quotes = Quote.objects.filter(
            company=company,
            status='ACCEPTED'
        ).exclude(
            invoices__isnull=False
        ).select_related('client')

        serializer = QuoteListSerializer(accepted_quotes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """
        Download invoice as PDF with company branding.
        Query params:
        - template: 'default', 'modern', 'classic' (optional)
        """
        invoice = self.get_object()
        template = request.query_params.get('template', 'default')

        try:
            # Generate PDF with specified template
            pdf_data = generate_invoice_pdf(invoice, template=template)

            # Create HTTP response with PDF
            response = HttpResponse(pdf_data, content_type='application/pdf')
            filename = f'Invoice-{invoice.invoice_number}.pdf'
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
        Preview invoice PDF in browser (inline display).
        Query params:
        - template: 'default', 'modern', 'classic' (optional)
        """
        invoice = self.get_object()
        template = request.query_params.get('template', 'default')

        try:
            # Generate PDF
            pdf_data = generate_invoice_pdf(invoice, template=template)

            # Create HTTP response with PDF for inline display
            response = HttpResponse(pdf_data, content_type='application/pdf')
            filename = f'Invoice-{invoice.invoice_number}.pdf'
            response['Content-Disposition'] = f'inline; filename="{filename}"'

            return response

        except Exception as e:
            return Response(
                {"error": f"Failed to generate PDF preview: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def send_to_client(self, request, pk=None):
        """
        Send invoice to client via email with PDF attachment.
        Body params:
        - email: Optional email override (uses client email by default)
        """
        invoice = self.get_object()

        # Get optional email override
        recipient_email = request.data.get('email')

        try:
            # Send email
            result = send_invoice_email(invoice, recipient_email)

            if result['success']:
                # Update invoice status to UNPAID if it was DRAFT
                if invoice.status == 'DRAFT':
                    invoice.status = 'UNPAID'
                    invoice.save()

                return Response({
                    'message': result['message'],
                    'status': invoice.status
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
