from django.contrib import admin
from .models import Quote, QuoteLineItem, Invoice, InvoiceLineItem, Payment


class QuoteLineItemInline(admin.TabularInline):
    model = QuoteLineItem
    extra = 1
    readonly_fields = ['line_total']


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ['quote_number', 'client', 'status', 'total_amount', 'date_issued', 'created_by']
    list_filter = ['status', 'date_issued', 'company']
    search_fields = ['quote_number', 'client__name']
    readonly_fields = ['quote_number', 'subtotal', 'tax_amount', 'total_amount', 'created_at', 'updated_at']
    inlines = [QuoteLineItemInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'client', 'quote_number', 'status')
        }),
        ('Dates', {
            'fields': ('date_issued', 'expiration_date')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'tax_rate', 'tax_amount', 'total_amount')
        }),
        ('Additional Information', {
            'fields': ('notes', 'terms')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(QuoteLineItem)
class QuoteLineItemAdmin(admin.ModelAdmin):
    list_display = ['quote', 'product_name', 'quantity', 'unit_price', 'discount_value', 'line_total']
    list_filter = ['quote__company']
    search_fields = ['product_name', 'product_sku', 'quote__quote_number']
    readonly_fields = ['line_total']


# ==================== INVOICE ADMIN ====================

class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 1
    readonly_fields = ['line_total']


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ['recorded_by', 'created_at']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'client', 'status', 'total_amount', 'amount_paid', 'amount_due', 'due_date', 'created_by']
    list_filter = ['status', 'issue_date', 'due_date', 'company']
    search_fields = ['invoice_number', 'client__name']
    readonly_fields = ['invoice_number', 'subtotal', 'tax_amount', 'total_amount', 'amount_paid', 'amount_due', 'is_overdue', 'created_at', 'updated_at']
    inlines = [InvoiceLineItemInline, PaymentInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'client', 'invoice_number', 'quote', 'status')
        }),
        ('Dates', {
            'fields': ('issue_date', 'due_date', 'is_overdue')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'tax_rate', 'tax_amount', 'total_amount', 'amount_paid', 'amount_due')
        }),
        ('Additional Information', {
            'fields': ('notes', 'terms')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(InvoiceLineItem)
class InvoiceLineItemAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'product_name', 'quantity', 'unit_price', 'discount_value', 'line_total']
    list_filter = ['invoice__company']
    search_fields = ['product_name', 'product_sku', 'invoice__invoice_number']
    readonly_fields = ['line_total']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'amount', 'payment_date', 'payment_method', 'recorded_by']
    list_filter = ['payment_method', 'payment_date', 'invoice__company']
    search_fields = ['invoice__invoice_number', 'reference']
    readonly_fields = ['recorded_by', 'created_at']
