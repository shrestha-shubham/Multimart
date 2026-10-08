from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from products.models import Product


class Cart(models.Model):
    customer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer.username}'s Cart"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'product'],
                name='unique_cart_product'
            )
        ]

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class Coupon(models.Model):
    DISCOUNT_TYPES = (
        ('percent', 'Percentage'),
        ('fixed', 'Fixed amount'),
    )

    code = models.CharField(max_length=32, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def clean(self):
        if self.discount_type == 'percent' and self.discount_value > 100:
            raise ValidationError({'discount_value': 'Percentage discounts cannot exceed 100%.'})
        if self.discount_value <= 0:
            raise ValidationError({'discount_value': 'Discount value must be greater than zero.'})
        if self.starts_at and self.expires_at and self.expires_at <= self.starts_at:
            raise ValidationError({'expires_at': 'Expiry must be later than the start time.'})

    @property
    def is_valid_now(self):
        now = timezone.now()
        return (
            self.is_active
            and (self.starts_at is None or self.starts_at <= now)
            and (self.expires_at is None or self.expires_at >= now)
            and (self.usage_limit is None or self.usage_count < self.usage_limit)
        )

    def __str__(self):
        return self.code


class Order(models.Model):
    PAYMENT_CHOICES = (
        ('cod', 'Cash on Delivery'),
        ('online', 'Online Payment'),
    )
    DELIVERY_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders'
    )

    order_number = models.CharField(
        max_length=20,
        unique=True
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    delivery_name = models.CharField(max_length=150, default='')

    delivery_phone = models.CharField(max_length=30, default='')

    delivery_address = models.TextField(default='')

    # Structured, immutable-at-order-time delivery address snapshot.
    delivery_province = models.CharField(max_length=40, blank=True, default='')
    delivery_district = models.CharField(max_length=80, blank=True, default='')
    delivery_municipality = models.CharField(max_length=120, blank=True, default='')
    delivery_ward = models.PositiveSmallIntegerField(null=True, blank=True)
    delivery_tole = models.CharField(max_length=150, blank=True, default='')
    delivery_landmark = models.CharField(max_length=255, blank=True, default='')

    delivery_status = models.CharField(
        max_length=20,
        choices=DELIVERY_STATUS_CHOICES,
        default='pending',
    )

    coupon = models.ForeignKey(
        Coupon,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='orders',
    )

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.order_number


class CustomerAddress(models.Model):
    """A customer's reusable checkout address; orders keep their own snapshot."""

    customer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delivery_address_profile',
    )
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    province = models.CharField(max_length=40)
    district = models.CharField(max_length=80)
    municipality = models.CharField(max_length=120)
    ward = models.PositiveSmallIntegerField()
    tole = models.CharField(max_length=150)
    landmark = models.CharField(max_length=255, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.customer}: {self.municipality}, {self.district}'


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )

    store = models.ForeignKey(
        'sellers.Store',
        on_delete=models.PROTECT,
        related_name='order_items'
    )

    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.order.order_number} - {self.product.name}"
