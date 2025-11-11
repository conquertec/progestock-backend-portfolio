from rest_framework import serializers
from .models import Supplier, PurchaseOrder, PurchaseOrderLineItem
from inventory.models import Product, Location
from decimal import Decimal


class SupplierSerializer(serializers.ModelSerializer):
    """
    Serializer for Supplier model.
    """
    class Meta:
        model = Supplier
        fields = [
            'id',
            'company',
            'name',
            'contact_person',
            'email',
            'phone',
            'address',
            'payment_terms',
            'lead_time_days',
            'notes',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'company', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Automatically set company from the request user
        validated_data['company'] = self.context['request'].user.company
        return super().create(validated_data)


class PurchaseOrderLineItemSerializer(serializers.ModelSerializer):
    """
    Serializer for purchase order line items.
    """
    product_details = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PurchaseOrderLineItem
        fields = [
            'id',
            'product',
            'product_name',
            'product_sku',
            'quantity_ordered',
            'quantity_received',
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
            'purchase_price': float(obj.product.purchase_price),
        }


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for purchase order list view.
    """
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    receiving_location_name = serializers.CharField(source='receiving_location.name', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id',
            'po_number',
            'supplier',
            'supplier_name',
            'status',
            'status_display',
            'order_date',
            'expected_delivery_date',
            'received_date',
            'receiving_location',
            'receiving_location_name',
            'subtotal',
            'tax_amount',
            'shipping_cost',
            'total_amount',
            'stock_added',
            'created_by_email',
            'created_at',
            'updated_at',
        ]


class PurchaseOrderDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for creating/editing purchase orders.
    Includes nested line items.
    """
    line_items = PurchaseOrderLineItemSerializer(many=True, required=False)
    supplier_details = serializers.SerializerMethodField(read_only=True)
    location_details = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id',
            'company',
            'supplier',
            'supplier_details',
            'po_number',
            'status',
            'status_display',
            'order_date',
            'expected_delivery_date',
            'received_date',
            'receiving_location',
            'location_details',
            'subtotal',
            'tax_rate',
            'tax_amount',
            'shipping_cost',
            'total_amount',
            'notes',
            'terms',
            'stock_added',
            'line_items',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'company', 'created_by', 'po_number', 'subtotal', 'tax_amount', 'total_amount', 'stock_added', 'created_at', 'updated_at']

    def get_supplier_details(self, obj):
        """Return full supplier details."""
        return {
            'id': obj.supplier.id,
            'name': obj.supplier.name,
            'contact_person': obj.supplier.contact_person,
            'email': obj.supplier.email,
            'phone': obj.supplier.phone,
            'payment_terms': obj.supplier.payment_terms,
        }

    def get_location_details(self, obj):
        """Return location details."""
        return {
            'id': obj.receiving_location.id,
            'name': obj.receiving_location.name,
        }

    def create(self, validated_data):
        """Create a purchase order with line items."""
        line_items_data = validated_data.pop('line_items', [])

        # Set company and created_by from request user
        validated_data['company'] = self.context['request'].user.company
        validated_data['created_by'] = self.context['request'].user

        # Create the purchase order
        purchase_order = PurchaseOrder.objects.create(**validated_data)

        # Create line items
        for item_data in line_items_data:
            product = item_data['product']
            # Store product details at time of order
            item_data['product_name'] = product.name
            item_data['product_sku'] = product.sku

            line_item = PurchaseOrderLineItem.objects.create(
                purchase_order=purchase_order,
                **item_data
            )
            # Calculate line total
            line_item.calculate_line_total()

        # Calculate totals for the purchase order
        purchase_order.calculate_totals()

        return purchase_order

    def update(self, instance, validated_data):
        """Update a purchase order and its line items."""
        line_items_data = validated_data.pop('line_items', None)

        # Update purchase order fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If line items are provided, update them
        if line_items_data is not None:
            # Delete existing line items
            instance.line_items.all().delete()

            # Create new line items
            for item_data in line_items_data:
                product = item_data['product']
                item_data['product_name'] = product.name
                item_data['product_sku'] = product.sku

                line_item = PurchaseOrderLineItem.objects.create(
                    purchase_order=instance,
                    **item_data
                )
                line_item.calculate_line_total()

        # Recalculate totals
        instance.calculate_totals()

        return instance
