from decimal import Decimal
from io import BytesIO
from pathlib import Path

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from orders.models import Order, OrderItem
from products.models import Category, Product
from products.models import Review

from .models import Store


class ProductImageManagementTests(TestCase):
	def setUp(self):
		self.user_model = get_user_model()
		self.seller = self.user_model.objects.create_user(
			username='image-seller',
			password='test-password',
			role='seller',
		)
		self.store = Store.objects.create(
			owner=self.seller,
			name='Image Test Store',
			phone='555-0100',
			address='10 Photo Lane',
		)
		self.category = Category.objects.create(name='Photo Test Category')
		self.saved_image_paths = []
		self.client.force_login(self.seller)

	def tearDown(self):
		for path in self.saved_image_paths:
			if path.exists():
				path.unlink()
		super().tearDown()

	def image_upload(self, name):
		image_bytes = BytesIO()
		Image.new('RGB', (2, 2), '#087f7b').save(image_bytes, format='PNG')
		return SimpleUploadedFile(name, image_bytes.getvalue(), content_type='image/png')

	def product_form_data(self, name):
		return {
			'category': self.category.pk,
			'name': name,
			'description': 'Image management test product',
			'price': '12.50',
			'stock': '4',
			'is_active': 'on',
		}

	def add_product(self, name, image=None):
		data = self.product_form_data(name)
		if image is not None:
			data['image'] = image
		response = self.client.post(reverse('seller_product_add'), data)
		self.assertRedirects(response, reverse('seller_products'))
		product = Product.objects.get(store=self.store, name=name)
		if product.image:
			self.saved_image_paths.append(Path(product.image.path))
		return product

	def test_seller_product_list_and_mutations_are_store_scoped(self):
		own_product = self.add_product('Own Store Product')
		other_owner = self.user_model.objects.create_user(
			username='other-store-owner', password='test-password', role='seller'
		)
		other_store = Store.objects.create(
			owner=other_owner, name='Other Store', phone='555-0101', address='Other address'
		)
		other_product = Product.objects.create(
			store=other_store, name='Other Store Product', price='15.00', stock=2
		)

		listing = self.client.get(reverse('seller_products'))
		self.assertContains(listing, own_product.name)
		self.assertNotContains(listing, other_product.name)
		self.assertEqual(
			self.client.get(reverse('seller_product_edit', args=[other_product.pk])).status_code,
			404,
		)
		self.assertEqual(
			self.client.post(reverse('seller_product_delete', args=[other_product.pk])).status_code,
			404,
		)
		self.assertTrue(Product.objects.filter(pk=other_product.pk).exists())

	def test_seller_product_delete_requires_post_and_only_deletes_own_product(self):
		product = self.add_product('Delete Me')
		self.assertEqual(
			self.client.get(reverse('seller_product_delete', args=[product.pk])).status_code,
			405,
		)
		response = self.client.post(reverse('seller_product_delete', args=[product.pk]))
		self.assertRedirects(response, reverse('seller_products'))
		self.assertFalse(Product.objects.filter(pk=product.pk).exists())

	def test_seller_can_add_image_and_it_renders_on_product_pages(self):
		product = self.add_product('Uploaded Product', self.image_upload('seller-upload-test.png'))

		self.assertEqual(product.image.name, 'products/seller-upload-test.png')
		self.assertTrue(Path(product.image.path).is_file())
		self.assertEqual(product.image.url, '/media/products/seller-upload-test.png')
		self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)
		self.assertContains(self.client.get(reverse('home')), product.image.url)
		self.assertContains(
			self.client.get(reverse('product-detail', args=[product.pk])),
			product.image.url,
		)
		self.assertContains(self.client.get(reverse('seller_products')), product.image.url)

	def test_seller_can_add_without_image_and_fallback_is_rendered(self):
		product = self.add_product('No Photo Product')

		self.assertFalse(product.image)
		self.assertContains(
			self.client.get(reverse('home')),
			'/static/images/product-placeholder.svg',
		)
		self.assertContains(
			self.client.get(reverse('product-detail', args=[product.pk])),
			'/static/images/product-placeholder.svg',
		)

	def test_seller_edit_preserves_photo_until_replacement_is_selected(self):
		product = self.add_product('Editable Photo Product', self.image_upload('seller-original-test.png'))
		original_name = product.image.name
		edit_url = reverse('seller_product_edit', args=[product.pk])

		edit_page = self.client.get(edit_url)
		self.assertContains(edit_page, product.image.url)
		self.assertContains(edit_page, 'enctype="multipart/form-data"')

		self.client.post(edit_url, self.product_form_data(product.name))
		product.refresh_from_db()
		self.assertEqual(product.image.name, original_name)

		self.client.post(
			edit_url,
			{
				**self.product_form_data(product.name),
				'image': self.image_upload('seller-replacement-test.png'),
			},
		)
		product.refresh_from_db()
		self.saved_image_paths.append(Path(product.image.path))
		self.assertEqual(product.image.name, 'products/seller-replacement-test.png')

	def test_admin_can_view_and_replace_product_image(self):
		product = self.add_product('Admin Photo Product', self.image_upload('admin-original-test.png'))
		admin_user = self.user_model.objects.create_superuser(
			username='image-admin',
			email='image-admin@example.test',
			password='test-password',
		)
		self.client.force_login(admin_user)
		change_url = reverse('admin:products_product_change', args=[product.pk])

		admin_page = self.client.get(change_url)
		self.assertEqual(admin_page.status_code, 200)
		self.assertContains(admin_page, 'name="image"')
		self.assertContains(admin_page, product.image.url)

		response = self.client.post(change_url, {
			**self.product_form_data(product.name),
			'store': self.store.pk,
			'image': self.image_upload('admin-replacement-test.png'),
			'_save': 'Save',
		})
		self.assertEqual(response.status_code, 302)
		product.refresh_from_db()
		self.saved_image_paths.append(Path(product.image.path))
		self.assertEqual(product.image.name, 'products/admin-replacement-test.png')


class SellerReviewDashboardTests(TestCase):
	def test_dashboard_aggregates_delivered_earnings_and_product_reviews(self):
		seller = get_user_model().objects.create_user(
			username='review-dashboard-seller',
			password='SellerPass!2026',
			role='seller',
		)
		customer = get_user_model().objects.create_user(
			username='review-dashboard-customer',
			password='CustomerPass!2026',
			first_name='Review',
			last_name='Buyer',
		)
		store = Store.objects.create(
			owner=seller,
			name='Review Dashboard Store',
			phone='555-0121',
			address='21 Review Road',
		)
		product = Product.objects.create(
			store=store,
			name='Reviewed Headphones',
			price='25.00',
			stock=5,
		)
		order = Order.objects.create(
			customer=customer,
			order_number='MMREVDASH0001',
			total_amount='25.00',
			payment_method='cod',
			delivery_name='Review Buyer',
			delivery_phone='555-0122',
			delivery_address='22 Review Road',
			delivery_status='delivered',
		)
		order_item = OrderItem.objects.create(
			order=order,
			product=product,
			store=store,
			quantity=1,
			unit_price=product.price,
			subtotal=product.price,
		)
		Review.objects.create(
			product=product,
			customer=customer,
			order_item=order_item,
			rating=5,
			comment='Excellent sound quality.',
		)
		self.client.force_login(seller)

		response = self.client.get(reverse('dashboard'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Total Earnings')
		self.assertContains(response, 'Total Ratings')
		self.assertContains(response, 'Excellent sound quality.')
		self.assertEqual(response.context['total_earnings'], Decimal('25.00'))
		self.assertEqual(response.context['total_reviews'], 1)
