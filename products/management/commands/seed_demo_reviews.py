import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from orders.models import Order, OrderItem
from products.models import Product, Review


COMMENTS = (
    'Exactly as described and arrived in great condition.',
    'Great value and the quality feels excellent.',
    'Works well so far. I would happily recommend it.',
    'A smooth purchase and a useful product for everyday use.',
    'Very happy with this order. The product feels well made.',
    'Good quality and fast delivery. I would buy from this store again.',
)


class Command(BaseCommand):
    help = 'Create ten demo customers with delivered purchases and verified product reviews.'

    @transaction.atomic
    def handle(self, *args, **options):
        randomizer = random.Random(20261007)
        products = list(
            Product.objects.filter(is_active=True, stock__gt=10)
            .select_related('store')
            .order_by('pk')
        )
        if not products:
            raise CommandError('Add active, in-stock products before seeding demo reviews.')

        review_products = randomizer.sample(products, min(5, len(products)))
        user_model = get_user_model()
        created_orders = 0
        created_reviews = 0

        for buyer_number in range(1, 11):
            username = f'demo_buyer_{buyer_number:02d}'
            customer, user_created = user_model.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.test',
                    'first_name': f'Demo Buyer {buyer_number}',
                    'role': 'customer',
                },
            )
            if user_created:
                customer.set_unusable_password()
                customer.save(update_fields=['password'])

            product = review_products[(buyer_number - 1) % len(review_products)]
            order_number = f'MMDEMO{buyer_number:06d}'
            order, order_created = Order.objects.get_or_create(
                order_number=order_number,
                defaults={
                    'customer': customer,
                    'total_amount': product.price,
                    'discount_amount': 0,
                    'payment_method': 'cod',
                    'delivery_name': customer.get_full_name(),
                    'delivery_phone': f'555-02-{buyer_number:04d}',
                    'delivery_address': f'{buyer_number} Demo Lane, Kathmandu',
                    'delivery_status': 'delivered',
                },
            )
            if not order_created and order.delivery_status != 'delivered':
                order.delivery_status = 'delivered'
                order.save(update_fields=['delivery_status'])

            order_item, item_created = OrderItem.objects.get_or_create(
                order=order,
                product=product,
                defaults={
                    'store': product.store,
                    'quantity': 1,
                    'unit_price': product.price,
                    'subtotal': product.price,
                },
            )
            if order_created and item_created:
                product.stock -= 1
                product.save(update_fields=['stock', 'updated_at'])
                created_orders += 1

            if randomizer.random() < 0.8:
                _, review_created = Review.objects.get_or_create(
                    order_item=order_item,
                    defaults={
                        'product': product,
                        'customer': customer,
                        'rating': randomizer.randint(3, 5),
                        'comment': randomizer.choice(COMMENTS),
                    },
                )
                created_reviews += int(review_created)

        self.stdout.write(self.style.SUCCESS(
            f'Ensured 10 demo customers with delivered purchases. '
            f'Created {created_orders} orders and {created_reviews} reviews '
            f'across {len(review_products)} products. No coupons were created.'
        ))