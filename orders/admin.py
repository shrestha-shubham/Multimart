from django.contrib import admin

from .models import Cart, CartItem, Coupon, Order, OrderItem


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('customer', 'created_at', 'updated_at')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'customer',
        'total_amount',
        'payment_method',
        'delivery_status',
        'coupon',
        'created_at',
    )

    list_display_links = ('order_number',)

    list_editable = ('delivery_status',)

    search_fields = (
        'order_number',
        'customer__username',
    )

    list_filter = (
        'payment_method',
        'delivery_status',
        'created_at',
    )

    readonly_fields = ('order_number', 'customer', 'total_amount', 'discount_amount', 'created_at')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'discount_type',
        'discount_value',
        'is_active',
        'usage_count',
        'usage_limit',
        'starts_at',
        'expires_at',
    )
    list_filter = ('is_active', 'discount_type')
    search_fields = ('code',)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'order',
        'product',
        'store',
        'quantity',
        'unit_price',
        'subtotal',
    )