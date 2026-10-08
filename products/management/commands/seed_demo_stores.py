from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from products.models import Category, Product
from sellers.models import Store


# Store, main category, product names. Prices are demo values in Nepalese rupees.
DEMO_STORES = (
    ('TechZone Nepal', 'Electronics', (
        ('Samsung Galaxy A56', '45000.00'), ('Redmi Note 14', '29999.00'),
        ('JBL Tune 520BT', '4999.00'), ('20W USB-C Charger', '1499.00'),
    )),
    ('Mobile Hub Kathmandu', 'Mobiles', (
        ('Samsung Galaxy A56', '45000.00'), ('iPhone 15', '119999.00'),
        ('Redmi Note 14', '29999.00'), ('10,000mAh Power Bank', '2499.00'),
    )),
    ('Gadget Ghar', 'Gadgets', (
        ('Redmi Note 14', '29999.00'), ('JBL Tune 520BT', '4999.00'),
        ('Logitech M185 Mouse', '1599.00'), ('20W USB-C Charger', '1499.00'),
    )),
    ('Digital World Nepal', 'Computers', (
        ('HP Laptop 15', '89999.00'), ('Logitech M185 Mouse', '1599.00'),
        ('Mechanical Keyboard', '5999.00'), ('24" Monitor', '22999.00'),
    )),
    ("Urban Wear Nepal", "Men's Fashion", (
        ("Men's Oversized T-Shirt", '1499.00'), ('Slim Fit Jeans', '2999.00'),
        ('Sneakers', '4999.00'), ('Hooded Jacket', '3999.00'),
    )),
    ('Style Studio', "Women's Fashion", (
        ("Women's Kurti", '1999.00'), ('Handbag', '2499.00'),
        ('Sneakers', '4999.00'), ('Denim Jacket', '3499.00'),
    )),
    ('Fashion Point', 'Fashion', (
        ('Slim Fit Jeans', '2999.00'), ('Oversized T-Shirt', '1499.00'),
        ('Sneakers', '4999.00'), ('Casual Shirt', '1999.00'),
    )),
    ('Sajilo Fashion', 'Clothing', (
        ("Women's Kurti", '1999.00'), ('Cotton Saree', '3499.00'),
        ('Casual Shirt', '1999.00'), ('Handbag', '2499.00'),
    )),
    ('Beauty Basket Nepal', 'Beauty', (
        ('Face Wash', '499.00'), ('Sunscreen SPF 50', '899.00'),
        ('Lipstick', '699.00'), ('Moisturizer', '799.00'),
    )),
    ('Glow & Care', 'Beauty', (
        ('Face Wash', '499.00'), ('Sunscreen SPF 50', '899.00'),
        ('Shampoo', '599.00'), ('Moisturizer', '799.00'),
    )),
    ('HomeStyle Nepal', 'Home', (
        ('Bedsheet Set', '2499.00'), ('LED Table Lamp', '1599.00'),
        ('Storage Box', '999.00'), ('Wall Clock', '1299.00'),
    )),
    ('Ghar Sajawat', 'Home Decor', (
        ('LED Table Lamp', '1599.00'), ('Wall Clock', '1299.00'),
        ('Decorative Vase', '1199.00'), ('Bedsheet Set', '2499.00'),
    )),
    ('Kitchen Corner', 'Kitchen', (
        ('Non-Stick Frying Pan', '1799.00'), ('Electric Kettle', '2199.00'),
        ('Lunch Box', '699.00'), ('Water Bottle', '499.00'),
    )),
    ('Daily Needs Mart', 'Grocery', (
        ('Basmati Rice 5kg', '1199.00'), ('Sunflower Oil 1L', '299.00'),
        ('Wai Wai Noodles', '25.00'), ('Green Tea', '399.00'),
    )),
    ('Fresh Basket Nepal', 'Grocery', (
        ('Basmati Rice 5kg', '1199.00'), ('Sunflower Oil 1L', '299.00'),
        ('Organic Honey', '899.00'), ('Green Tea', '399.00'),
    )),
    ('Himalayan Foods', 'Nepali Food', (
        ('Organic Honey', '899.00'), ('Gundruk 500g', '399.00'),
        ('Nepali Achar 1kg', '499.00'), ('Himalayan Tea', '599.00'),
    )),
    ('Sports Hub Nepal', 'Sports', (
        ('Yoga Mat', '1499.00'), ('Football', '1999.00'),
        ('Skipping Rope', '499.00'), ('Sports Shoes', '5999.00'),
    )),
    ('Active Life Store', 'Fitness', (
        ('Yoga Mat', '1499.00'), ('Skipping Rope', '499.00'),
        ('Dumbbell Set', '3499.00'), ('Sports Shoes', '5999.00'),
    )),
    ('BookPoint Nepal', 'Books & Stationery', (
        ('Python Programming Book', '1299.00'), ('Notebook Set', '499.00'),
        ('Scientific Calculator', '1499.00'), ('Ball Pen Pack', '199.00'),
    )),
    ('Student Corner', 'Education', (
        ('Python Programming Book', '1299.00'), ('Notebook Set', '499.00'),
        ('Scientific Calculator', '1499.00'), ('Backpack', '2499.00'),
    )),
)

PRODUCT_IMAGES = (
    'products/samsung-galaxy-a56.svg',
    'products/wireless-noise-canceling-headphones.svg',
    'products/smart-fitness-watch.svg',
    'products/portable-ssd-1tb.svg',
    'products/gaming-laptop.svg',
)


class Command(BaseCommand):
    help = 'Replace the demo marketplace catalog with 20 Nepal stores and their listed products.'

    @transaction.atomic
    def handle(self, *args, **options):
        user_model = get_user_model()
        # Hide listings from the previous version of this demo seed, retaining
        # old order and review records for referential integrity.
        Product.objects.filter(store__owner__username__startswith='multimart_demo_').update(is_active=False)
        products_added = 0

        for store_number, (store_name, main_category, products) in enumerate(DEMO_STORES, start=1):
            username = f'multimart_demo_{slugify(store_name).replace("-", "_")}'
            owner, created = user_model.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.test',
                    'first_name': store_name,
                    'role': 'seller',
                },
            )
            if created:
                owner.set_unusable_password()
                owner.save(update_fields=['password'])

            store, _ = Store.objects.update_or_create(
                owner=owner,
                defaults={
                    'name': store_name,
                    'description': f'{store_name} offers quality products in {main_category.lower()} from Kathmandu, Nepal.',
                    'phone': f'+977 980000{store_number:04d}',
                    'address': f'{store_number} Market Road, Kathmandu, Nepal',
                },
            )
            category, _ = Category.objects.get_or_create(name=main_category)

            for product_number, (product_name, price) in enumerate(products):
                _, created = Product.objects.update_or_create(
                    store=store,
                    name=product_name,
                    defaults={
                        'category': category,
                        'description': f'{product_name} from {store_name}.',
                        'price': price,
                        'stock': 20,
                        'image': PRODUCT_IMAGES[(store_number + product_number) % len(PRODUCT_IMAGES)],
                        'is_active': True,
                    },
                )
                products_added += int(created)

        self.stdout.write(self.style.SUCCESS(
            f'Ensured {len(DEMO_STORES)} demo stores and {len(DEMO_STORES) * 4} listed products. '
            f'Added {products_added} products; database now has '
            f'{Store.objects.count()} stores and {Product.objects.count()} products.'
        ))
