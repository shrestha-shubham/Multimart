from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from sellers.models import Store

from .models import Category, Product


class HomeCategoryTests(TestCase):
	def setUp(self):
		self.seller = get_user_model().objects.create_user(username='seller')
		store = Store.objects.create(
			owner=self.seller,
			name='Test Store',
			phone='555-0100',
			address='Test address',
		)
		category = Category.objects.create(name='Audio')
		self.categorized_product = Product.objects.create(
			store=store,
			category=category,
			name='Test Headphones',
			description='Wireless headphones',
			price='49.99',
			stock=5,
			image='products/wireless-noise-canceling-headphones.svg',
		)
		self.uncategorized_product = Product.objects.create(
			store=store,
			name='Test Accessory',
			description='A useful accessory',
			price='9.99',
			stock=3,
		)

	def test_home_groups_categories_and_renders_product_images(self):
		response = self.client.get(reverse('home'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(
			response,
			f'data-category-filter="{self.categorized_product.category_id}"',
		)
		self.assertContains(response, self.categorized_product.name)

	def test_store_owner_sees_your_product_without_add_to_cart(self):
		self.client.force_login(self.seller)
		response = self.client.get(
			reverse('store-profile', args=[self.categorized_product.store_id])
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Your product')
		self.assertNotContains(response, 'Add to Cart')
		self.assertContains(response, self.categorized_product.image.url)
		self.assertContains(response, self.uncategorized_product.name)
		self.assertContains(
			response,
			reverse('store-profile', args=[self.categorized_product.store_id]),
		)

	def test_store_name_opens_public_store_profile(self):
		response = self.client.get(
			reverse('store-profile', args=[self.categorized_product.store_id])
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self.categorized_product.store.name)
		self.assertContains(response, self.categorized_product.name)

	def test_home_search_matches_product_names_in_database(self):
		response = self.client.get(reverse('home'), {'q': 'headPHONES'})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self.categorized_product.name)
		self.assertNotContains(response, self.uncategorized_product.name)
		self.assertEqual(response.context['search_query'], 'headPHONES')
		self.assertContains(response, 'name="q"')
