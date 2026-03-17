from django.contrib import admin
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = (
        'id', 'customer', 'product', 'quantity', 'total',
        'payment_method', 'payment_status', 'status', 'created',
    )
    list_filter   = ('status', 'payment_method', 'payment_status', 'created')
    search_fields = ('customer__username', 'product__name', 'razorpay_order_id', 'razorpay_payment_id')
    readonly_fields = (
        'customer', 'vendor', 'product', 'variant', 'quantity', 'total',
        'address', 'pincode', 'payment_method', 'payment_status',
        'razorpay_order_id', 'razorpay_payment_id', 'created', 'updated',
    )
    fieldsets = (
        ('Order Info', {
            'fields': ('customer', 'vendor', 'product', 'variant', 'quantity', 'total', 'address', 'pincode')
        }),
        ('Payment', {
            'fields': ('payment_method', 'payment_status', 'razorpay_order_id', 'razorpay_payment_id')
        }),
        ('Status', {
            'fields': ('status', 'cancel_reason', 'cancel_note')
        }),
        ('Timestamps', {
            'fields': ('created', 'updated')
        }),
    )

