from django.contrib import admin
from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1
    fields = ('product', 'quantity', 'unit_price', 'subtotal')
    readonly_fields = ('subtotal',)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'client', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'company')
    search_fields = ('client__name', 'notes')
    inlines = [SaleItemInline]
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'client', 'user', 'status')
        }),
        ('Financial', {
            'fields': ('total_amount',)
        }),
        ('Additional Details', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'sale', 'product', 'quantity', 'unit_price', 'subtotal')
    list_filter = ('sale__status', 'created_at')
    search_fields = ('product__name', 'sale__id')
    readonly_fields = ('subtotal', 'created_at')
