from django.contrib import admin
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'industry', 'currency', 'onboarding_complete', 'created_at']
    list_filter = ['onboarding_complete', 'currency', 'created_at']
    search_fields = ['name', 'industry']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'industry', 'logo')
        }),
        ('Sales & Quote Settings', {
            'fields': ('currency', 'sales_tax_name', 'sales_tax_rate', 'payment_terms')
        }),
        ('AI Profile', {
            'fields': ('business_profile',),
            'classes': ('collapse',)
        }),
        ('Onboarding Status', {
            'fields': ('onboarding_complete',),
            'description': 'Toggle this to control whether the setup wizard reminder appears for users.'
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
