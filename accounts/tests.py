from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from decimal import Decimal

from sellers.models import Store
from orders.models import Order
from products.models import Product


class LoginPageTests(TestCase):
	def test_login_page_renders_without_google_oauth_configuration(self):
		response = self.client.get('/login/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'name="username"')
		self.assertNotContains(response, 'Continue with Google')


class RegistrationTests(TestCase):
	def test_registration_page_renders(self):
		response = self.client.get('/register/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Create account')
		self.assertContains(response, 'id_role')

	def test_customer_can_register_and_is_logged_in(self):
		response = self.client.post('/register/', {
			'username': 'newcustomer',
			'email': 'customer@example.com',
			'role': 'customer',
			'password1': 'StrongPass!237',
			'password2': 'StrongPass!237',
		})

		self.assertRedirects(response, '/dashboard/')
		user = get_user_model().objects.get(username='newcustomer')
		self.assertEqual(user.role, 'customer')
		self.assertIn('_auth_user_id', self.client.session)
		self.assertFalse(Store.objects.filter(owner=user).exists())

	def test_seller_registration_creates_store(self):
		response = self.client.post('/register/', {
			'username': 'newseller',
			'email': 'seller@example.com',
			'role': 'seller',
			'password1': 'StrongPass!237',
			'password2': 'StrongPass!237',
			'store_name': 'Fresh Finds',
			'phone': '555-0100',
			'address': '12 Market Street',
		})

		self.assertRedirects(response, '/dashboard/')
		user = get_user_model().objects.get(username='newseller')
		self.assertEqual(user.role, 'seller')
		self.assertEqual(user.store.name, 'Fresh Finds')
		self.assertEqual(user.store.phone, '555-0100')
		self.assertEqual(user.store.address, '12 Market Street')

	def test_seller_registration_requires_store_details(self):
		response = self.client.post('/register/', {
			'username': 'incompleteseller',
			'email': 'incomplete@example.com',
			'role': 'seller',
			'password1': 'StrongPass!237',
			'password2': 'StrongPass!237',
		})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'required for seller accounts')
		self.assertFalse(get_user_model().objects.filter(username='incompleteseller').exists())


class ProfilePageTests(TestCase):
	def setUp(self):
		self.customer = get_user_model().objects.create_user(
			username='profilecustomer',
			password='test-password',
			first_name='Ari',
		)
		self.client.force_login(self.customer)

	def test_customer_profile_opens_from_dashboard_and_saves_changes(self):
		dashboard = self.client.get(reverse('dashboard'))
		self.assertContains(dashboard, f'href="{reverse("profile")}"')

		response = self.client.get(reverse('profile'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'My Profile')
		self.assertContains(response, 'Save Profile')

		response = self.client.post(reverse('profile'), {
			'first_name': 'Ari',
			'last_name': 'Morgan',
			'email': 'ari@example.com',
		})
		self.assertRedirects(response, reverse('profile'))
		self.customer.refresh_from_db()
		self.assertEqual(self.customer.last_name, 'Morgan')
		self.assertEqual(self.customer.email, 'ari@example.com')

	def test_seller_profile_link_opens_store_profile_editor(self):
		seller = get_user_model().objects.create_user(
			username='profileseller',
			password='test-password',
			role='seller',
		)
		self.client.force_login(seller)

		response = self.client.get(reverse('profile'))
		self.assertRedirects(response, reverse('seller_profile'))
		response = self.client.get(reverse('seller_profile'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Store Profile')

	def test_authenticated_marketplace_shows_working_logout_link(self):
		homepage = self.client.get(reverse('home'))
		self.assertContains(homepage, 'Dashboard')
		self.assertContains(homepage, f'href="{reverse("dashboard")}"')
		self.assertContains(homepage, 'Manage account')
		self.assertContains(homepage, 'My Orders')
		self.assertContains(homepage, 'Sign out')
		self.assertContains(homepage, 'Add account')

		add_account = self.client.get(
			f'{reverse("logout")}?next={reverse("register")}'
		)
		self.assertRedirects(add_account, reverse('register'))
		self.assertNotIn('_auth_user_id', self.client.session)
		self.assertEqual(self.client.get(reverse('register')).status_code, 200)

		self.client.force_login(self.customer)

		response = self.client.get(reverse('logout'))
		self.assertRedirects(response, reverse('login'))
		self.assertNotIn('_auth_user_id', self.client.session)

		anonymous_homepage = self.client.get(reverse('home'))
		self.assertNotContains(anonymous_homepage, f'href="{reverse("logout")}"')


class AdminDashboardTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.admin = user_model.objects.create_superuser(
			username='approved-admin',
			email='admin@example.test',
			password='AdminDemo!2026',
			first_name='Approved',
		)
		self.seller = user_model.objects.create_user(
			username='dashboard-seller',
			password='SellerDemo!2026',
			role='seller',
		)
		self.store = Store.objects.create(
			owner=self.seller,
			name='Dashboard Test Store',
			phone='555-0110',
			address='1 Admin Way',
		)
		Product.objects.create(
			store=self.store,
			name='Dashboard Test Product',
			price='25.00',
			stock=3,
		)
		Order.objects.create(
			customer=user_model.objects.create_user(username='dashboard-customer'),
			order_number='ADMINTEST0001',
			total_amount=Decimal('25.00'),
			payment_method='cod',
			delivery_name='Dashboard Customer',
			delivery_phone='555-0120',
			delivery_address='2 Admin Way',
		)

	def test_approved_admin_sees_dashboard_and_store_records(self):
		self.client.force_login(self.admin)

		response = self.client.get(reverse('dashboard'))
		self.assertRedirects(response, reverse('admin-dashboard'))

		response = self.client.get(reverse('admin-dashboard'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Admin Dashboard')
		self.assertContains(response, 'aria-label="MultiMart home"')
		self.assertContains(response, f'href="{reverse("home")}"')
		self.assertContains(response, 'ADMINTEST0001')
		self.assertEqual(response.context['total_products'], 1)
		self.assertEqual(response.context['total_orders'], 1)
		self.assertEqual(response.context['total_stores'], 1)

		stores = self.client.get(reverse('admin-stores'))
		self.assertEqual(stores.status_code, 200)
		self.assertContains(stores, 'Dashboard Test Store')

	def test_non_admin_cannot_access_admin_dashboard_or_store_list(self):
		self.client.force_login(self.seller)

		self.assertEqual(self.client.get(reverse('admin-dashboard')).status_code, 403)
		self.assertEqual(self.client.get(reverse('admin-stores')).status_code, 403)

	def test_registration_cannot_self_assign_admin_role(self):
		response = self.client.post(reverse('register'), {
			'username': 'self-approved-admin',
			'email': 'self-admin@example.test',
			'role': 'admin',
			'password1': 'StrongPass!237',
			'password2': 'StrongPass!237',
		})

		self.assertEqual(response.status_code, 200)
		self.assertFalse(get_user_model().objects.filter(username='self-approved-admin').exists())

