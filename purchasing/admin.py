from django.contrib import admin
from .models import Supplier, PurchaseOrder, PurchaseOrderLineItem


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'contact_person', 'email')
    ordering = ('name',)


class PurchaseOrderLineItemInline(admin.TabularInline):
    model = PurchaseOrderLineItem
    extra = 1
    fields = ('product', 'quantity_ordered', 'quantity_received', 'unit_price', 'discount_type', 'discount_value', 'line_total')
    readonly_fields = ('line_total',)


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier', 'status', 'order_date', 'total_amount', 'stock_added', 'created_at')
    list_filter = ('status', 'stock_added', 'order_date', 'created_at')
    search_fields = ('po_number', 'supplier__name')
    ordering = ('-created_at',)
    inlines = [PurchaseOrderLineItemInline]
    readonly_fields = ('subtotal', 'tax_amount', 'total_amount', 'stock_added')

    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'supplier', 'po_number', 'status', 'receiving_location')
        }),
        ('Dates', {
            'fields': ('order_date', 'expected_delivery_date', 'received_date')
        }),
        ('Financial Information', {
            'fields': ('subtotal', 'tax_rate', 'tax_amount', 'shipping_cost', 'total_amount')
        }),
        ('Additional Info', {
            'fields': ('notes', 'terms', 'stock_added', 'created_by')
        }),
    )
