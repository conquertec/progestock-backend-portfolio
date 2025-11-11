from rest_framework import serializers
from .models import Quote, QuoteLineItem, Invoice, InvoiceLineItem, Payment
from inventory.models import Client, Product


class QuoteLineItemSerializer(serializers.ModelSerializer):
    """
    Serializer for quote line items.
    """
    product_details = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = QuoteLineItem
        fields = [
            'id',
            'product',
            'product_name',
            'product_sku',
            'quantity',
            'unit_price',
            'discount_type',
            'discount_value',
            'line_total',
            'product_details',
        ]
        read_only_fields = ['line_total', 'product_name', 'product_sku']

    def get_product_details(self, obj):
        """Return full product details for display."""
        return {
            'id': obj.product.id,
            'name': obj.product.name,
            'sku': obj.product.sku,
            'price': float(obj.product.price),
        }


class QuoteListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for quote list view.
    """
    client_name = serializers.CharField(source='client.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    has_invoice = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Quote
        fields = [
            'id',
            'quote_number',
            'client',
            'client_name',
            'status',
            'status_display',
            'date_issued',
            'expiration_date',
            'subtotal',
            'tax_amount',
            'total_amount',
            'created_by_email',
            'created_at',
            'updated_at',
            'has_invoice',
        ]

    def get_has_invoice(self, obj):
        """Return True if this quote has been converted to an invoice."""
        return obj.invoices.exists()


class QuoteDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for creating/editing quotes.
    Includes nested line items.
    """
    line_items = QuoteLineItemSerializer(many=True, required=False)
    client_details = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Quote
        fields = [
            'id',
            'quote_number',
            'client',
            'client_details',
            'status',
            'status_display',
            'date_issued',
            'expiration_date',
            'subtotal',
            'tax_rate',
            'tax_amount',
            'total_amount',
            'notes',
            'terms',
            'line_items',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['quote_number', 'subtotal', 'tax_amount', 'total_amount']

    def get_client_details(self, obj):
        """Return full client details for display."""
        return {
            'id': obj.client.id,
            'name': obj.client.name,
            'email': obj.client.email,
            'phone': obj.client.phone,
            'address': obj.client.address,
        }

    def create(self, validated_data):
        line_items_data = validated_data.pop('line_items', [])
        quote = Quote.objects.create(**validated_data)

        # Create line items
        for line_item_data in line_items_data:
            QuoteLineItem.objects.create(quote=quote, **line_item_data)

        # Calculate totals
        quote.calculate_totals()

        return quote

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop('line_items', None)

        # Update quote fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update line items if provided
        if line_items_data is not None:
            # Delete existing line items
            instance.line_items.all().delete()

            # Create new line items
            for line_item_data in line_items_data:
                QuoteLineItem.objects.create(quote=instance, **line_item_data)

        # Recalculate totals
        instance.calculate_totals()

        return instance


# ==================== INVOICE SERIALIZERS ====================

class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for payment records.
    """
    recorded_by_email = serializers.CharField(source='recorded_by.email', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id',
            'invoice',
            'amount',
            'payment_date',
            'payment_method',
            'payment_method_display',
            'reference',
            'notes',
            'recorded_by_email',
            'created_at',
        ]
        read_only_fields = ['recorded_by_email']


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    """
    Serializer for invoice line items.
    """
    product_details = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = InvoiceLineItem
        fields = [
            'id',
            'product',
            'product_name',
            'product_sku',
            'quantity',
            'unit_price',
            'discount_type',
            'discount_value',
            'line_total',
            'product_details',
        ]
        read_only_fields = ['line_total', 'product_name', 'product_sku']

    def get_product_details(self, obj):
        """Return full product details for display."""
        return {
            'id': obj.product.id,
            'name': obj.product.name,
            'sku': obj.product.sku,
            'price': float(obj.product.price),
        }


class InvoiceListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for invoice list view.
    """
    client_name = serializers.CharField(source='client.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    amount_due = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id',
            'invoice_number',
            'client',
            'client_name',
            'status',
            'status_display',
            'issue_date',
            'due_date',
            'subtotal',
            'tax_amount',
            'total_amount',
            'amount_paid',
            'amount_due',
            'is_overdue',
            'stock_reduced',
            'created_at',
            'updated_at',
        ]


class InvoiceDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for creating/editing invoices.
    Includes nested line items and payments.
    """
    line_items = InvoiceLineItemSerializer(many=True, required=False)
    payments = PaymentSerializer(many=True, read_only=True)
    client_details = serializers.SerializerMethodField(read_only=True)
    quote_details = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    amount_due = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id',
            'invoice_number',
            'client',
            'client_details',
            'quote',
            'quote_details',
            'status',
            'status_display',
            'issue_date',
            'due_date',
            'subtotal',
            'tax_rate',
            'tax_amount',
            'total_amount',
            'amount_paid',
            'amount_due',
            'is_overdue',
            'stock_reduced',
            'notes',
            'terms',
            'line_items',
            'payments',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['invoice_number', 'subtotal', 'tax_amount', 'total_amount', 'amount_paid', 'stock_reduced']

    def get_client_details(self, obj):
        """Return full client details for display."""
        return {
            'id': obj.client.id,
            'name': obj.client.name,
            'email': obj.client.email,
            'phone': obj.client.phone,
            'address': obj.client.address,
        }

    def get_quote_details(self, obj):
        """Return quote details if this invoice was created from a quote."""
        if obj.quote:
            return {
                'id': obj.quote.id,
                'quote_number': obj.quote.quote_number,
                'date_issued': obj.quote.date_issued,
                'expiration_date': obj.quote.expiration_date,
                'status': obj.quote.status,
                'status_display': obj.quote.get_status_display(),
            }
        return None

    def create(self, validated_data):
        line_items_data = validated_data.pop('line_items', [])
        invoice = Invoice.objects.create(**validated_data)

        # Create line items
        for line_item_data in line_items_data:
            InvoiceLineItem.objects.create(invoice=invoice, **line_item_data)

        # Calculate totals
        invoice.calculate_totals()

        return invoice

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop('line_items', None)

        # Update invoice fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update line items if provided
        if line_items_data is not None:
            # Delete existing line items
            instance.line_items.all().delete()

            # Create new line items
            for line_item_data in line_items_data:
                InvoiceLineItem.objects.create(invoice=instance, **line_item_data)

        # Recalculate totals
        instance.calculate_totals()

        return instance
