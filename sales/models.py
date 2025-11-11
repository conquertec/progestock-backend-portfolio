from django.db import models
from django.conf import settings
from company.models import Company
from inventory.models import Client, Product
from decimal import Decimal


class Quote(models.Model):
    """
    Represents a sales quote sent to a client.
    """
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('INVOICED', 'Invoiced'),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='quotes')
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='quotes')
    quote_number = models.CharField(max_length=50, unique=True, help_text="Unique quote identifier")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    date_issued = models.DateField(help_text="Date the quote was created or sent")
    expiration_date = models.DateField(help_text="Date when the quote expires")

    # Financial fields
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text="Tax rate as a percentage")
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Additional info
    notes = models.TextField(blank=True, help_text="Internal notes about the quote")
    terms = models.TextField(blank=True, help_text="Payment terms and conditions")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='quotes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['quote_number']),
            models.Index(fields=['status']),
            models.Index(fields=['date_issued']),
        ]

    def __str__(self):
        return f"{self.quote_number} - {self.client.name} - {self.get_status_display()}"

    def calculate_totals(self):
        """
        Calculate and update the quote totals based on line items.
        """
        line_items = self.line_items.all()
        self.subtotal = sum(
            (item.line_total for item in line_items),
            Decimal('0.00')  # Start with Decimal to preserve type
        )
        self.tax_amount = (self.subtotal * self.tax_rate) / Decimal('100')
        self.total_amount = self.subtotal + self.tax_amount
        self.save()


class QuoteLineItem(models.Model):
    """
    Represents a single product line in a quote.
    Stores the price at the time of quote creation to preserve the quote value
    even if product prices change later.
    """
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='line_items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='quote_line_items')

    # Store product details at the time of quote creation
    product_name = models.CharField(max_length=255, help_text="Product name at time of quote")
    product_sku = models.CharField(max_length=100, blank=True, help_text="Product SKU at time of quote")

    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per unit at time of quote")

    # Discount can be percentage or fixed amount
    discount_type = models.CharField(
        max_length=10,
        choices=(('PERCENTAGE', 'Percentage'), ('FIXED', 'Fixed Amount')),
        default='PERCENTAGE'
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product_name} x{self.quantity} - {self.quote.quote_number}"

    def calculate_line_total(self):
        """
        Calculate the line total including discounts.
        """
        base_total = self.quantity * self.unit_price

        if self.discount_type == 'PERCENTAGE':
            discount_amount = (base_total * self.discount_value) / Decimal('100')
        else:  # FIXED
            discount_amount = self.discount_value

        self.line_total = base_total - discount_amount
        self.save()

    def save(self, *args, **kwargs):
        # Auto-populate product details if not set
        if not self.product_name:
            self.product_name = self.product.name
        if not self.product_sku:
            self.product_sku = self.product.sku
        if not self.unit_price:
            self.unit_price = self.product.price

        # Calculate line total before saving
        base_total = self.quantity * self.unit_price
        if self.discount_type == 'PERCENTAGE':
            discount_amount = (base_total * self.discount_value) / Decimal('100')
        else:
            discount_amount = self.discount_value
        self.line_total = base_total - discount_amount

        super().save(*args, **kwargs)


class Invoice(models.Model):
    """
    Represents an invoice sent to a client for payment.
    """
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('UNPAID', 'Unpaid'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
        ('PARTIALLY_PAID', 'Partially Paid'),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='invoices')
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='invoices')
    invoice_number = models.CharField(max_length=50, help_text="Unique invoice identifier per company")

    # Link to original quote if created from one
    quote = models.ForeignKey(Quote, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    issue_date = models.DateField(help_text="Date the invoice was issued")
    due_date = models.DateField(help_text="Date when payment is due")
    paid_date = models.DateTimeField(null=True, blank=True, help_text="Date when the invoice was marked as paid")

    # Financial fields
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text="Tax rate as a percentage")
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Amount paid so far")

    # Additional info
    notes = models.TextField(blank=True, help_text="Internal notes about the invoice")
    terms = models.TextField(blank=True, help_text="Payment terms and conditions")

    # Stock tracking
    stock_reduced = models.BooleanField(default=False, help_text="Whether stock has been reduced for this invoice")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='invoices_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['company', 'invoice_number']]
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['status']),
            models.Index(fields=['issue_date']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.client.name} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        """
        Override save to handle stock reduction when invoice is marked as PAID.
        """
        # Skip custom logic if this is just updating specific fields (like stock_reduced)
        # This prevents recursion when reduce_stock() calls save(update_fields=['stock_reduced'])
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            super().save(*args, **kwargs)
            return

        # Check if this is an update (not a new instance)
        if self.pk:
            # Get the old instance from database
            try:
                old_instance = Invoice.objects.get(pk=self.pk)
                # Check if status just changed to PAID
                if old_instance.status != 'PAID' and self.status == 'PAID':
                    # Status changed to PAID, save first then reduce stock
                    super().save(*args, **kwargs)
                    if not self.stock_reduced:
                        self.reduce_stock()
                    return
            except Invoice.DoesNotExist:
                pass

        # Normal save
        super().save(*args, **kwargs)

    @property
    def amount_due(self):
        """Calculate the remaining amount due."""
        return self.total_amount - self.amount_paid

    @property
    def is_overdue(self):
        """Check if the invoice is overdue."""
        from datetime import date
        return self.status in ['UNPAID', 'PARTIALLY_PAID'] and self.due_date < date.today()

    def calculate_totals(self):
        """
        Calculate and update the invoice totals based on line items.
        """
        line_items = self.line_items.all()
        self.subtotal = sum(
            (item.line_total for item in line_items),
            Decimal('0.00')  # Start with Decimal to preserve type
        )
        self.tax_amount = (self.subtotal * self.tax_rate) / Decimal('100')
        self.total_amount = self.subtotal + self.tax_amount
        self.save()

    def reduce_stock(self):
        """
        Reduce stock quantities for all line items in the invoice.
        This should only be called once when the invoice is paid.
        """
        from inventory.models import Stock
        from auditing.models import LogEntry

        if self.stock_reduced:
            # Stock already reduced, don't do it again
            return

        # Reduce stock for each line item
        for line_item in self.line_items.all():
            # Get all stock locations for this product
            stocks = Stock.objects.filter(
                product=line_item.product,
                product__company=self.company
            ).order_by('-quantity')

            remaining_qty = line_item.quantity

            # Reduce stock from locations with highest quantity first
            for stock in stocks:
                if remaining_qty <= 0:
                    break

                if stock.quantity >= remaining_qty:
                    # This location has enough stock
                    stock.quantity -= remaining_qty
                    stock.save()

                    # Log the stock reduction
                    LogEntry.objects.create(
                        company=self.company,
                        user=None,  # System action
                        action_type='STOCK_REMOVED',
                        details={
                            'model': 'Stock',
                            'stock_id': stock.id,
                            'product_name': line_item.product_name,
                            'quantity_reduced': str(remaining_qty),
                            'invoice_number': self.invoice_number,
                            'message': f'Reduced stock by {remaining_qty} for invoice {self.invoice_number}'
                        }
                    )

                    remaining_qty = 0
                else:
                    # Take all available stock from this location
                    qty_taken = stock.quantity
                    stock.quantity = 0
                    stock.save()

                    # Log the stock reduction
                    LogEntry.objects.create(
                        company=self.company,
                        user=None,  # System action
                        action_type='STOCK_REMOVED',
                        details={
                            'model': 'Stock',
                            'stock_id': stock.id,
                            'product_name': line_item.product_name,
                            'quantity_reduced': str(qty_taken),
                            'invoice_number': self.invoice_number,
                            'message': f'Reduced stock by {qty_taken} for invoice {self.invoice_number}'
                        }
                    )

                    remaining_qty -= qty_taken

            if remaining_qty > 0:
                # Not enough stock - log a warning
                LogEntry.objects.create(
                    company=self.company,
                    user=None,
                    action_type='STOCK_LEVEL_ADJUSTED',
                    details={
                        'model': 'Invoice',
                        'invoice_id': self.id,
                        'product_name': line_item.product_name,
                        'quantity_needed': str(line_item.quantity),
                        'quantity_short': str(remaining_qty),
                        'invoice_number': self.invoice_number,
                        'message': f'Insufficient stock for {line_item.product_name}: needed {line_item.quantity}, short by {remaining_qty}'
                    }
                )

        # Mark stock as reduced
        self.stock_reduced = True
        self.save(update_fields=['stock_reduced'])

    def update_status(self):
        """
        Update invoice status based on payment and due date.
        Reduces stock when invoice is marked as PAID.
        """
        from datetime import date
        from django.utils import timezone

        # Store old status to detect changes
        old_status = self.status

        # If DRAFT and no payment, keep as DRAFT
        if self.status == 'DRAFT' and self.amount_paid == 0:
            return

        if self.amount_paid == 0:
            # Only auto-update from DRAFT to UNPAID/OVERDUE if explicitly needed
            if self.status == 'DRAFT':
                return
            if self.due_date < date.today():
                self.status = 'OVERDUE'
            else:
                self.status = 'UNPAID'
        elif self.amount_paid >= self.total_amount:
            self.status = 'PAID'
            # Set paid_date if status just changed to PAID
            if old_status != 'PAID':
                self.paid_date = timezone.now()
        else:
            if self.due_date < date.today():
                self.status = 'OVERDUE'
            else:
                self.status = 'PARTIALLY_PAID'

        # Save status change
        self.save()

        # If status just changed to PAID, reduce stock
        if self.status == 'PAID' and old_status != 'PAID' and not self.stock_reduced:
            self.reduce_stock()


class InvoiceLineItem(models.Model):
    """
    Represents a single product line in an invoice.
    """
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='line_items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='invoice_line_items')

    # Store product details at the time of invoice creation
    product_name = models.CharField(max_length=255, help_text="Product name at time of invoice")
    product_sku = models.CharField(max_length=100, blank=True, help_text="Product SKU at time of invoice")

    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per unit at time of invoice")

    # Discount can be percentage or fixed amount
    discount_type = models.CharField(
        max_length=10,
        choices=(('PERCENTAGE', 'Percentage'), ('FIXED', 'Fixed Amount')),
        default='PERCENTAGE'
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product_name} x{self.quantity} - {self.invoice.invoice_number}"

    def save(self, *args, **kwargs):
        # Auto-populate product details if not set
        if not self.product_name:
            self.product_name = self.product.name
        if not self.product_sku:
            self.product_sku = self.product.sku
        if not self.unit_price:
            self.unit_price = self.product.price

        # Calculate line total before saving
        base_total = self.quantity * self.unit_price
        if self.discount_type == 'PERCENTAGE':
            discount_amount = (base_total * self.discount_value) / Decimal('100')
        else:
            discount_amount = self.discount_value
        self.line_total = base_total - discount_amount

        super().save(*args, **kwargs)


class Payment(models.Model):
    """
    Represents a payment received for an invoice.
    """
    PAYMENT_METHOD_CHOICES = (
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CREDIT_CARD', 'Credit Card'),
        ('CASH', 'Cash'),
        ('CHECK', 'Check'),
        ('PAYPAL', 'PayPal'),
        ('OTHER', 'Other'),
    )

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount paid")
    payment_date = models.DateField(help_text="Date payment was received")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='BANK_TRANSFER')
    reference = models.CharField(max_length=255, blank=True, help_text="Transaction ID or reference number")
    notes = models.TextField(blank=True, help_text="Additional notes about the payment")

    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='payments_recorded')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment of {self.amount} for {self.invoice.invoice_number}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Update invoice amount_paid - use Decimal to avoid type mismatch
        self.invoice.amount_paid = sum(
            (payment.amount for payment in self.invoice.payments.all()),
            Decimal('0.00')  # Start with Decimal to preserve type
        )
        self.invoice.update_status()
        self.invoice.save()
