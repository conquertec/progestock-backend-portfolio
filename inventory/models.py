from django.db import models
from django.conf import settings
from company.models import Company
from decimal import Decimal
import uuid

def product_image_upload_path(instance, filename):
    """
    Generates a unique path for each product image.
    e.g., product_images/a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d.jpg
    """
    ext = filename.split('.')[-1]
    unique_id = uuid.uuid4()
    new_filename = f"{unique_id}.{ext}"
    return f'product_images/{new_filename}'

class Location(models.Model):
    """
    Represents a physical location where inventory is stored.
    e.g., 'Main Warehouse', 'Shop Floor'
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='locations')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.company.name})"

class Category(models.Model):
    """
    Represents a category for products.
    e.g., 'Electronics', 'Clothing', 'Raw Materials'
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Product(models.Model):
    """
    Represents an inventory item with multilingual support.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, blank=True, default='', help_text="Stock Keeping Unit")
    
    description_en = models.TextField(blank=True, help_text="Product description in English.")
    description_fr = models.TextField(blank=True, help_text="Product description in French.")

    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="The selling price of the product.")
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="The cost/purchase price of the product for profit calculations.")
    reorder_threshold = models.PositiveIntegerField(default=10, help_text="Stock level at which to trigger a low-stock alert.")
    image = models.ImageField(upload_to=product_image_upload_path, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Stock(models.Model):
    """
    Represents the quantity of a specific product at a specific location.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_levels')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='stock_levels')
    quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'location')

    def __str__(self):
        return f"{self.product.name} at {self.location.name}: {self.quantity}"

# --- THE FIX: Add the missing Client model ---
class Client(models.Model):
    """
    Represents a customer or client of the company.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='clients')
    name = models.CharField(max_length=255, help_text="The client's full name or company name.")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name