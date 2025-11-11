from rest_framework import serializers
from .models import Company

class CompanySerializer(serializers.ModelSerializer):
    """
    Serializer for the Company model.
    Now includes validation to limit the logo file size.
    """
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = ['id', 'name', 'industry', 'currency', 'language', 'logo', 'logo_url', 'business_profile', 'onboarding_complete', 'brand_color']
        read_only_fields = ['business_profile', 'logo_url']

    def get_logo_url(self, obj):
        """
        Return the full URL for the logo if it exists.
        """
        if obj.logo:
            return obj.logo.url
        return None

    def validate_logo(self, value):
        """
        Custom validator for the logo field.
        """
        # Check if a file was even provided. If not, that's fine.
        if value is None:
            return value

        # --- THE FIX: Enforce a file size limit ---
        # Set a maximum size for the logo, e.g., 2 MB.
        max_size = 2 * 1024 * 1024  # 2MB in bytes
        if value.size > max_size:
            # If the file is too large, raise a validation error.
            # This will result in a 400 Bad Request response.
            raise serializers.ValidationError('The logo file size cannot exceed 2MB.')
        # ----------------------------------------

        # If the file size is acceptable, return the file to continue processing.
        return value


class UpdateCompanySerializer(serializers.ModelSerializer):
    """
    Serializer for updating company settings.
    Allows updates to all company fields including financial settings.
    """
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            'id', 'name', 'industry', 'currency', 'language', 'logo', 'logo_url',
            'business_profile', 'sales_tax_name', 'sales_tax_rate',
            'payment_terms', 'brand_color', 'created_at', 'onboarding_complete'
        ]
        read_only_fields = ['id', 'created_at']

    def get_logo_url(self, obj):
        """
        Return the full URL for the logo if it exists.
        When using GCS with django-storages, obj.logo.url already returns
        the full GCS URL (signed or public), so we don't need build_absolute_uri.
        """
        if obj.logo:
            # obj.logo.url already contains the full GCS URL
            return obj.logo.url
        return None

    def validate_logo(self, value):
        """Validate logo file size."""
        if value is None:
            return value

        max_size = 2 * 1024 * 1024  # 2MB
        if value.size > max_size:
            raise serializers.ValidationError('The logo file size cannot exceed 2MB.')
        return value

    def validate_sales_tax_rate(self, value):
        """Validate that sales tax rate is between 0 and 100."""
        if value < 0 or value > 100:
            raise serializers.ValidationError('Sales tax rate must be between 0 and 100.')
        return value

    def validate_brand_color(self, value):
        """Validate that brand_color is a valid hex color code."""
        # If empty, return default color
        if not value or value == '':
            return '#3B82F6'

        import re
        # Check if it's a valid hex color (with or without #)
        hex_pattern = re.compile(r'^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')
        if not hex_pattern.match(value):
            raise serializers.ValidationError('Brand color must be a valid hex color code (e.g., #3B82F6).')

        # Ensure it starts with #
        if not value.startswith('#'):
            value = '#' + value

        return value  # Return as provided (hex colors are case-insensitive)