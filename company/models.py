from django.db import models
from decimal import Decimal
import uuid

# A helper function to define the upload path for logos
def company_logo_upload_path(instance, filename):
    """
    Generates a unique path for each uploaded logo.
    Example: logos/a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d.png
    """
    ext = filename.split('.')[-1]
    unique_id = uuid.uuid4()
    new_filename = f"{unique_id}.{ext}"
    return f'logos/{new_filename}'

class Company(models.Model):
    """
    Stores all information related to a user's company.
    """
    # --- Existing Onboarding Fields ---
    name = models.CharField(max_length=255, help_text="The official name of the company.")
    industry = models.CharField(max_length=100, help_text="The industry the company operates in.")
    currency = models.CharField(max_length=3, help_text="The default currency code (e.g., USD, EUR).")
    language = models.CharField(max_length=2, default='en', help_text="The default language code (e.g., en, fr).")
    logo = models.ImageField(upload_to=company_logo_upload_path, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    onboarding_complete = models.BooleanField(default=False)

    # --- AI-Related Field ---
    business_profile = models.TextField(blank=True, help_text="An AI-generated summary of the business.")

    # --- NEW Sales & Quote Settings ---
    sales_tax_name = models.CharField(max_length=50, blank=True, default="Tax", help_text="The default name for sales tax (e.g., VAT, GST).")
    sales_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text="The default sales tax rate as a percentage (e.g., 18.5).")
    payment_terms = models.CharField(max_length=100, blank=True, default="Due on receipt", help_text="Default payment terms for invoices and quotes.")
    # ------------------------------------

    # --- Brand Customization ---
    brand_color = models.CharField(max_length=7, blank=True, default="#3B82F6", help_text="Primary brand color extracted from logo (hex format, e.g., #3B82F6).")
    # ---------------------------

    def __str__(self):
        return self.name

