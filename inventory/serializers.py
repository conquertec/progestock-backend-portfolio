from rest_framework import serializers
from .models import Location, Category, Product, Client, Stock

class LocationSerializer(serializers.ModelSerializer):
    usage_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Location
        fields = ['id', 'name', 'usage_count']

class CategorySerializer(serializers.ModelSerializer):
    usage_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Category
        fields = ['id', 'name', 'usage_count']

class ClientSerializer(serializers.ModelSerializer):
    """
    Serializer for Client with calculated fields for CRM insights.
    Includes lifetime value, outstanding amount, last activity, and counts.
    """
    # Calculated read-only fields
    lifetime_value = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, default=0.00)
    amount_outstanding = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, default=0.00)
    last_activity = serializers.DateField(read_only=True, allow_null=True)
    total_quotes = serializers.IntegerField(read_only=True, default=0)
    total_invoices = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Client
        fields = [
            'id', 'name', 'email', 'phone', 'address',
            'lifetime_value', 'amount_outstanding', 'last_activity',
            'total_quotes', 'total_invoices', 'created_at'
        ]

class StockSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating stock records.
    """
    class Meta:
        model = Stock
        fields = ['id', 'product', 'location', 'quantity']

class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer for the Product model. Includes calculated fields for total stock
    and stock status, the category name, and the product image.
    """
    # Read-only fields to provide extra, useful information in GET requests.
    category_name = serializers.CharField(source='category.name', read_only=True)
    total_quantity = serializers.IntegerField(read_only=True)
    stock_status = serializers.CharField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'sku',
            'category', # Used for writing (creating/updating)
            'category_name', # Used for reading
            'price',
            'purchase_price',
            'description_en',
            'description_fr',
            'reorder_threshold',
            'image',
            'total_quantity',
            'stock_status',
        ]
        # Make the 'category' field write-only since we display 'category_name'
        extra_kwargs = {
            'category': {'write_only': True, 'required': False, 'allow_null': True},
        }

class StockLevelDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for stock levels in the Stock Control page.
    Includes product details, location details, and calculated values.
    """
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_image = serializers.ImageField(source='product.image', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    reorder_threshold = serializers.IntegerField(source='product.reorder_threshold', read_only=True)

    location_id = serializers.IntegerField(source='location.id', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)

    total_value = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = [
            'id',
            'product_id',
            'product_name',
            'product_sku',
            'product_image',
            'product_price',
            'reorder_threshold',
            'location_id',
            'location_name',
            'quantity',
            'total_value',
            'stock_status',
            'updated_at',
        ]

    def get_total_value(self, obj):
        """Calculate the total value of this stock entry."""
        return float(obj.quantity * obj.product.price)

    def get_stock_status(self, obj):
        """Determine the stock status based on quantity and reorder threshold."""
        if obj.quantity == 0:
            return 'Out of Stock'
        elif obj.quantity <= obj.product.reorder_threshold:
            return 'Low Stock'
        return 'In Stock'

class StockAdjustmentSerializer(serializers.Serializer):
    """
    Serializer for adjusting stock levels.
    """
    ADJUSTMENT_ACTIONS = (
        ('add', 'Add to Stock'),
        ('remove', 'Remove from Stock'),
        ('set', 'Set New Quantity'),
    )

    product = serializers.IntegerField(help_text="Product ID")
    location = serializers.IntegerField(help_text="Location ID")
    action = serializers.ChoiceField(choices=ADJUSTMENT_ACTIONS)
    quantity = serializers.IntegerField(min_value=0, help_text="Quantity to adjust")
    reason = serializers.CharField(max_length=255, help_text="Reason for adjustment")

    def validate(self, data):
        """Validate the adjustment data."""
        # Ensure product and location exist and belong to the user's company
        try:
            product = Product.objects.get(id=data['product'])
            location = Location.objects.get(id=data['location'])
        except (Product.DoesNotExist, Location.DoesNotExist):
            raise serializers.ValidationError("Invalid product or location.")

        data['product_obj'] = product
        data['location_obj'] = location

        return data

class StockTransferSerializer(serializers.Serializer):
    """
    Serializer for transferring stock between locations.
    """
    product = serializers.IntegerField(help_text="Product ID")
    from_location = serializers.IntegerField(help_text="Source Location ID")
    to_location = serializers.IntegerField(help_text="Destination Location ID")
    quantity = serializers.IntegerField(min_value=1, help_text="Quantity to transfer")
    reason = serializers.CharField(max_length=255, help_text="Reason for transfer")

    def validate(self, data):
        """Validate the transfer data."""
        # Ensure from_location and to_location are different
        if data['from_location'] == data['to_location']:
            raise serializers.ValidationError("Source and destination locations must be different.")

        # Ensure product and locations exist
        try:
            product = Product.objects.get(id=data['product'])
            from_location = Location.objects.get(id=data['from_location'])
            to_location = Location.objects.get(id=data['to_location'])
        except (Product.DoesNotExist, Location.DoesNotExist):
            raise serializers.ValidationError("Invalid product or location.")

        # Ensure sufficient stock at the source location
        try:
            source_stock = Stock.objects.get(product=product, location=from_location)
            if source_stock.quantity < data['quantity']:
                raise serializers.ValidationError(
                    f"Insufficient stock at {from_location.name}. Available: {source_stock.quantity}"
                )
        except Stock.DoesNotExist:
            raise serializers.ValidationError(
                f"No stock record found for {product.name} at {from_location.name}."
            )

        data['product_obj'] = product
        data['from_location_obj'] = from_location
        data['to_location_obj'] = to_location
        data['source_stock_obj'] = source_stock

        return data

