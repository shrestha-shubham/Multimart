from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from sellers.models import Store


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='products'
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )

    name = models.CharField(max_length=200)

    description = models.TextField(blank=True)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    stock = models.PositiveIntegerField(default=0)

    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Review(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='product_reviews',
    )
    order_item = models.OneToOneField(
        'orders.OrderItem',
        on_delete=models.CASCADE,
        related_name='review',
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def clean(self):
        if not 1 <= self.rating <= 5:
            raise ValidationError({'rating': 'Rating must be between 1 and 5.'})
        if self.order_item_id:
            if self.order_item.product_id != self.product_id:
                raise ValidationError('Review product must match the purchased product.')
            if self.order_item.order.customer_id != self.customer_id:
                raise ValidationError('Only the customer who placed the order can review it.')
            if self.order_item.order.delivery_status != 'delivered':
                raise ValidationError('Products can only be reviewed after delivery.')

    def __str__(self):
        return f'{self.product.name}: {self.rating}/5 by {self.customer}'