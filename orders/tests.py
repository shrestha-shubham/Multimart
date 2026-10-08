from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from products.models import Product
from sellers.models import Store

from .models import Cart, CartItem, Coupon, CustomerAddress, Order, OrderItem
from products.models import Review


class OrderFlowTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.customer = user_model.objects.create_user(
			username='amira',
			password='test-password',
			first_name='Amira',
			last_name='Khan',
		)
		self.seller = user_model.objects.create_user(
			username='seller',
			password='test-password',
			role='seller',
		)
		store = Store.objects.create(
			owner=self.seller,
			name='Test Store',
			phone='555-0100',
			address='Store address',
		)
		self.product = Product.objects.create(
			store=store,
			name='Test Headphones',
			description='Wireless headphones',
			price='12.50',
			stock=8,
		)
		self.client.force_login(self.customer)

	def checkout_data(self, **overrides):
		data = {
			'full_name': 'Amira Khan',
			'phone': '+977 9812345678',
			'province': 'Bagmati Province',
			'district': 'Kathmandu',
			'municipality': 'Kathmandu Metropolitan City',
			'ward': '10',
			'tole': 'New Baneshwor',
			'landmark': 'Near XYZ',
			'payment_method': 'cod',
		}
		data.update(overrides)
		return data

	def test_product_quantity_updates_cart_and_is_limited_by_stock(self):
		detail = self.client.get(reverse('product-detail', args=[self.product.pk]))
		self.assertContains(detail, 'name="quantity"')
		self.assertContains(detail, 'max="8"')

		response = self.client.post(
			reverse('add-to-cart', args=[self.product.pk]),
			{'quantity': '3'},
		)
		self.assertRedirects(response, reverse('cart'))
		cart_item = CartItem.objects.get(product=self.product)
		self.assertEqual(cart_item.quantity, 3)

		self.client.post(
			reverse('update-cart-item', args=[cart_item.pk]),
			{'quantity': '5'},
		)
		cart_item.refresh_from_db()
		self.assertEqual(cart_item.quantity, 5)

		self.client.post(
			reverse('update-cart-item', args=[cart_item.pk]),
			{'quantity': '9'},
		)
		cart_item.refresh_from_db()
		self.assertEqual(cart_item.quantity, 5)

		self.client.post(reverse('remove-cart-item', args=[cart_item.pk]))
		self.assertFalse(CartItem.objects.filter(pk=cart_item.pk).exists())

	def test_checkout_creates_order_and_reduces_stock(self):
		cart = Cart.objects.create(customer=self.customer)
		CartItem.objects.create(cart=cart, product=self.product, quantity=2)

		response = self.client.post(reverse('checkout'), self.checkout_data())

		order = Order.objects.get(customer=self.customer)
		self.assertRedirects(
			response,
			reverse('order-confirmation', args=[order.order_number]),
		)
		order_item = OrderItem.objects.get(order=order)
		self.assertEqual(order_item.quantity, 2)
		self.assertEqual(order.total_amount, Decimal('25.00'))
		self.assertEqual(order.delivery_name, 'Amira Khan')
		self.assertEqual(order.delivery_province, 'Bagmati Province')
		self.assertEqual(order.delivery_district, 'Kathmandu')
		self.assertEqual(order.delivery_municipality, 'Kathmandu Metropolitan City')
		self.assertEqual(order.delivery_ward, 10)
		self.assertEqual(order.delivery_tole, 'New Baneshwor')
		self.product.refresh_from_db()
		self.assertEqual(self.product.stock, 6)
		self.assertFalse(cart.items.exists())

		confirmation = self.client.get(response.url)
		self.assertContains(confirmation, order.order_number)
		self.assertContains(confirmation, 'New Baneshwor')

	def test_checkout_rejects_quantity_above_available_stock(self):
		cart = Cart.objects.create(customer=self.customer)
		CartItem.objects.create(cart=cart, product=self.product, quantity=9)

		response = self.client.post(reverse('checkout'), self.checkout_data())

		self.assertRedirects(response, reverse('cart'))
		self.assertFalse(Order.objects.exists())
		self.product.refresh_from_db()
		self.assertEqual(self.product.stock, 8)

	def test_admin_coupon_is_applied_and_usage_is_recorded(self):
		coupon = Coupon.objects.create(
			code='save20',
			discount_type='percent',
			discount_value='20.00',
			usage_limit=5,
		)
		cart = Cart.objects.create(customer=self.customer)
		CartItem.objects.create(cart=cart, product=self.product, quantity=2)

		response = self.client.post(reverse('checkout'), self.checkout_data(coupon_code=' save20 '))

		order = Order.objects.get(customer=self.customer)
		self.assertRedirects(
			response,
			reverse('order-confirmation', args=[order.order_number]),
		)
		order.refresh_from_db()
		coupon.refresh_from_db()
		self.assertEqual(order.total_amount, Decimal('20.00'))
		self.assertEqual(order.discount_amount, Decimal('5.00'))
		self.assertEqual(order.coupon_id, coupon.pk)
		self.assertEqual(coupon.usage_count, 1)

	def test_invalid_coupon_keeps_cart_and_does_not_place_order(self):
		cart = Cart.objects.create(customer=self.customer)
		CartItem.objects.create(cart=cart, product=self.product, quantity=1)

		response = self.client.post(reverse('checkout'), self.checkout_data(coupon_code='NOT-A-COUPON'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'coupon is invalid')
		self.assertFalse(Order.objects.exists())
		self.assertTrue(cart.items.exists())

	def test_only_admin_can_change_order_delivery_status(self):
		order = Order.objects.create(
			customer=self.customer,
			order_number='MMSTATUS0001',
			total_amount='12.50',
			payment_method='cod',
			delivery_name='Amira Khan',
			delivery_phone='555-0142',
			delivery_address='42 Market Street',
		)
		change_url = reverse('admin:orders_order_change', args=[order.pk])

		seller_page = self.client.get(change_url)
		self.assertIn(seller_page.status_code, (302, 403))

		admin = get_user_model().objects.create_superuser(
			username='order-admin',
			email='order-admin@example.test',
			password='AdminPass!2026',
		)
		self.client.force_login(admin)
		admin_page = self.client.get(change_url)
		self.assertEqual(admin_page.status_code, 200)
		self.assertContains(admin_page, 'delivery_status')

		response = self.client.post(change_url, {
			'payment_method': 'cod',
			'delivery_name': order.delivery_name,
			'delivery_phone': order.delivery_phone,
			'delivery_address': order.delivery_address,
			'delivery_status': 'delivered',
			'coupon': '',
			'_save': 'Save',
		})
		self.assertEqual(response.status_code, 302)
		order.refresh_from_db()
		self.assertEqual(order.delivery_status, 'delivered')

	def test_review_requires_a_delivered_purchase(self):
		order = Order.objects.create(
			customer=self.customer,
			order_number='MMREVIEW0001',
			total_amount='12.50',
			payment_method='cod',
			delivery_name='Amira Khan',
			delivery_phone='555-0142',
			delivery_address='42 Market Street',
		)
		order_item = OrderItem.objects.create(
			order=order,
			product=self.product,
			store=self.product.store,
			quantity=1,
			unit_price=self.product.price,
			subtotal=self.product.price,
		)
		review_url = reverse('submit-review', args=[self.product.pk])

		response = self.client.post(review_url, {'rating': '5', 'comment': 'Great product.'})
		self.assertRedirects(response, reverse('product-detail', args=[self.product.pk]))
		self.assertFalse(Review.objects.exists())

		order.delivery_status = 'delivered'
		order.save(update_fields=['delivery_status'])
		response = self.client.post(review_url, {'rating': '5', 'comment': 'Great product.'})
		self.assertRedirects(response, reverse('product-detail', args=[self.product.pk]))
		review = Review.objects.get(order_item=order_item)
		self.assertEqual(review.rating, 5)
		self.assertContains(
			self.client.get(reverse('product-detail', args=[self.product.pk])),
			'Great product.',
		)

	def test_seller_sees_own_product_label_and_cannot_add_own_product(self):
		self.client.force_login(self.seller)
		homepage = self.client.get(reverse('home'))
		self.assertContains(homepage, 'Your product')
		self.assertNotContains(
			homepage,
			f'action="{reverse("add-to-cart", args=[self.product.pk])}"',
		)

		detail = self.client.get(reverse('product-detail', args=[self.product.pk]))
		self.assertContains(detail, 'Your product')
		self.assertNotContains(detail, 'Add to Cart')

		response = self.client.post(
			reverse('add-to-cart', args=[self.product.pk]),
			{'quantity': '1'},
		)
		self.assertRedirects(response, reverse('product-detail', args=[self.product.pk]))
		self.assertFalse(CartItem.objects.filter(cart__customer=self.seller).exists())

	def test_seller_can_add_another_stores_product(self):
		other_owner = get_user_model().objects.create_user(
			username='another-seller',
			password='test-password',
			role='seller',
		)
		other_store = Store.objects.create(
			owner=other_owner,
			name='Another Store',
			phone='555-0101',
			address='Other address',
		)
		other_product = Product.objects.create(
			store=other_store,
			name='Other Store Product',
			price='5.00',
			stock=4,
		)
		self.client.force_login(self.seller)

		response = self.client.post(
			reverse('add-to-cart', args=[other_product.pk]),
			{'quantity': '1'},
		)

		self.assertRedirects(response, reverse('cart'))
		self.assertEqual(
			CartItem.objects.get(cart__customer=self.seller, product=other_product).quantity,
			1,
		)
		checkout_response = self.client.post(
			reverse('checkout'),
			self.checkout_data(full_name='Seller Buyer'),
		)
		self.assertEqual(checkout_response.status_code, 302)
		self.assertTrue(Order.objects.filter(customer=self.seller, items__product=other_product).exists())

	def test_checkout_rejects_an_own_product_already_in_cart(self):
		cart = Cart.objects.create(customer=self.seller)
		CartItem.objects.create(cart=cart, product=self.product, quantity=1)
		self.client.force_login(self.seller)

		response = self.client.post(reverse('checkout'), self.checkout_data(full_name='Seller'))

		self.assertRedirects(response, reverse('cart'))
		self.assertFalse(Order.objects.filter(customer=self.seller).exists())
		self.assertTrue(cart.items.exists())

	def test_checkout_rejects_missing_required_address_field(self):
		CartItem.objects.create(cart=Cart.objects.create(customer=self.customer), product=self.product)
		response = self.client.post(reverse('checkout'), self.checkout_data(ward=''))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'This field is required.', html=False)
		self.assertFalse(Order.objects.exists())

	def test_checkout_rejects_invalid_nepal_phone(self):
		CartItem.objects.create(cart=Cart.objects.create(customer=self.customer), product=self.product)
		response = self.client.post(reverse('checkout'), self.checkout_data(phone='12345'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Enter a valid Nepal mobile number')
		self.assertFalse(Order.objects.exists())

	def test_checkout_rejects_district_from_another_province(self):
		CartItem.objects.create(cart=Cart.objects.create(customer=self.customer), product=self.product)
		response = self.client.post(reverse('checkout'), self.checkout_data(district='Jhapa'))

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.context['delivery_form'].errors['district'])
		self.assertFalse(Order.objects.exists())

	def test_checkout_rejects_municipality_from_another_district(self):
		CartItem.objects.create(cart=Cart.objects.create(customer=self.customer), product=self.product)
		response = self.client.post(reverse('checkout'), self.checkout_data(municipality='Pokhara Metropolitan City'))

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.context['delivery_form'].errors['municipality'])
		self.assertFalse(Order.objects.exists())

	def test_checkout_rejects_invalid_ward(self):
		CartItem.objects.create(cart=Cart.objects.create(customer=self.customer), product=self.product)
		response = self.client.post(reverse('checkout'), self.checkout_data(ward='abc'))

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.context['delivery_form'].errors['ward'])
		self.assertFalse(Order.objects.exists())

	def test_checkout_saves_reusable_address_when_requested(self):
		CartItem.objects.create(cart=Cart.objects.create(customer=self.customer), product=self.product)
		response = self.client.post(reverse('checkout'), self.checkout_data(save_address='on'))

		self.assertEqual(response.status_code, 302)
		saved_address = CustomerAddress.objects.get(customer=self.customer)
		self.assertEqual(saved_address.municipality, 'Kathmandu Metropolitan City')
		order = Order.objects.get(customer=self.customer)
		saved_address.district = 'Lalitpur'
		saved_address.save(update_fields=['district'])
		order.refresh_from_db()
		self.assertEqual(order.delivery_district, 'Kathmandu')

	def test_account_mark_uses_customer_name_initial(self):
		response = self.client.get(reverse('product-detail', args=[self.product.pk]))

		self.assertContains(response, 'aria-label="Open account menu for Amira Khan">')
