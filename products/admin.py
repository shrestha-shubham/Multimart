from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, Review


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'store',
        'category',
        'image_preview',
        'price',
        'stock',
        'is_active',
    )

    readonly_fields = ('image_preview',)

    list_filter = (
        'category',
        'store',
        'is_active',
    )

    search_fields = (
        'name',
        'store__name',
    )

    @admin.display(description='Product image')
    def image_preview(self, obj):
        if not obj or not obj.image:
            return 'No image uploaded'
        return format_html(
            '<img src="{}" alt="{}" style="width:72px;height:56px;object-fit:contain;background:#f5f7f4;border-radius:4px">',
            obj.image.url,
            obj.name,
        )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'customer', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'customer__username', 'comment')