from django.db import models
from django.conf import settings
from company.models import Company
from inventory.models import Product, Location
from decimal import Decimal


class Supplier(models.Model):
    """
    Represents a supplier/vendor from whom the company purchases inventory.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='suppliers')
    name = models.CharField(max_length=255, help_text="The supplier's company name")
    contact_person = models.CharField(max_length=255, blank=True, help_text="Primary contact person")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    # Purchasing details
    payment_terms = models.CharField(max_length=100, blank=True, help_text="e.g., 'Net 30', '50% upfront', etc.")
    lead_time_days = models.PositiveIntegerField(default=0, help_text="Typical delivery time in days")

    # Additional info
    notes = models.TextField(blank=True, help_text="Internal notes about the supplier")
    is_active = models.BooleanField(default=True, help_text="Whether this supplier is currently active")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    """
    Represents a purchase order sent to a supplier to restock inventory.
    """
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent to Supplier'),
        ('CONFIRMED', 'Confirmed by Supplier'),
        ('PARTIALLY_RECEIVED', 'Partially Received'),
        ('RECEIVED', 'Fully Received'),
        ('CANCELLED', 'Cancelled'),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='purchase_orders')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    po_number = models.CharField(max_length=50, unique=True, help_text="Unique purchase order identifier")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    # Dates
    order_date = models.DateField(help_text="Date the PO was created")
    expected_delivery_date = models.DateField(null=True, blank=True, help_text="Expected delivery date")
    received_date = models.DateField(null=True, blank=True, help_text="Date when fully received")

    # Location where stock will be received
    receiving_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        help_text="Location where items will be added to stock upon receipt"
    )

    # Financial fields
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text="Tax rate as a percentage")
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Shipping/delivery cost")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Additional info
    notes = models.TextField(blank=True, help_text="Internal notes about the purchase order")
    terms = models.TextField(blank=True, help_text="Payment terms and conditions")

    # Stock management
    stock_added = models.BooleanField(default=False, help_text="Whether stock has been added to inventory")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='purchase_orders_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['po_number']),
            models.Index(fields=['status']),
            models.Index(fields=['order_date']),
        ]

    def __str__(self):
        return f"{self.po_number} - {self.supplier.name} - {self.get_status_display()}"

    def calculate_totals(self):
        """
        Calculate and update the purchase order totals based on line items.
        """
        line_items = self.line_items.all()
        self.subtotal = sum(
            (item.line_total for item in line_items),
            Decimal('0.00')
        )
        self.tax_amount = (self.subtotal * self.tax_rate) / Decimal('100')
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_cost
        self.save()

    def add_stock_to_inventory(self):
        """
        Add received items to inventory at the receiving location.
        Only call this when the PO status is RECEIVED.
        """
        from inventory.models import Stock

        if self.stock_added:
            return {"error": "Stock already added for this purchase order"}

        if self.status != 'RECEIVED':
            return {"error": "Can only add stock for fully received orders"}

        for line_item in self.line_items.all():
            # Get or create stock record for this product at the receiving location
            stock, created = Stock.objects.get_or_create(
                product=line_item.product,
                location=self.receiving_location,
                defaults={'quantity': 0}
            )

            # Add the received quantity
            stock.quantity += line_item.quantity_received
            stock.save()

        # Mark that stock has been added
        self.stock_added = True
        self.save()

        return {"success": True, "message": "Stock added successfully"}


class PurchaseOrderLineItem(models.Model):
    """
    Represents a single product line in a purchase order.
    Stores the price at the time of PO creation.
    """
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='line_items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='purchase_order_line_items')

    # Store product details at the time of PO creation
    product_name = models.CharField(max_length=255, help_text="Product name at time of order")
    product_sku = models.CharField(max_length=100, blank=True, help_text="Product SKU at time of order")

    quantity_ordered = models.PositiveIntegerField(default=1, help_text="Quantity ordered from supplier")
    quantity_received = models.PositiveIntegerField(default=0, help_text="Quantity actually received")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Purchase price per unit")

    # Discount can be percentage or fixed amount
    discount_type = models.CharField(
        max_length=10,
        choices=(('PERCENTAGE', 'Percentage'), ('FIXED', 'Fixed Amount')),
        default='PERCENTAGE'
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product_name} x{self.quantity_ordered} - {self.purchase_order.po_number}"

    def calculate_line_total(self):
        """
        Calculate the line total based on quantity, unit price, and discount.
        """
        base_total = self.quantity_ordered * self.unit_price

        if self.discount_type == 'PERCENTAGE':
            discount_amount = (base_total * self.discount_value) / Decimal('100')
        else:  # FIXED
            discount_amount = self.discount_value

        self.line_total = base_total - discount_amount
        self.save()
        return self.line_total
