from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Store, Product

# A utility function to create a store quickly in tests
def create_store(owner, name, store_type, status):
    """Creates a store for testing purposes."""
    return Store.objects.create(owner=owner, name=name, store_type=store_type, status=status)

# A utility function to create a product quickly in tests
def create_product(store, name, price):
    """Creates a product for testing purposes."""
    return Product.objects.create(store=store, name=name, price=price)


class StoreViewPermissionsTests(TestCase):
    """
    Tests focused on user permissions and authorization for store-related views.
    """
    def setUp(self):
        # Create two distinct users to test ownership rules
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')

        # user1 owns an approved store and a pending store
        self.approved_store = create_store(self.user1, 'User1 Approved Store', 'PET', 'APPROVED')
        self.pending_store = create_store(self.user1, 'User1 Pending Store', 'SUPPLIES', 'PENDING')
        
        # user2 owns another approved store
        self.other_store = create_store(self.user2, 'User2 Approved Store', 'PET', 'APPROVED')

    def test_anonymous_user_redirected(self):
        """Anonymous users should be redirected to the login page for protected views."""
        protected_urls = [
            reverse('store_list'),
            reverse('store_request'),
            reverse('store_manage', kwargs={'pk': self.approved_store.pk}),
            reverse('store_update', kwargs={'pk': self.approved_store.pk}),
            reverse('product_create', kwargs={'pk': self.approved_store.pk}),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertRedirects(response, f'/accounts/login/?next={url}') # Assumes your LOGIN_URL is '/accounts/login/'

    def test_user_cannot_manage_other_users_store(self):
        """A logged-in user should get a 403 Forbidden error when trying to manage another user's store."""
        self.client.login(username='user2', password='password123')
        
        # user2 tries to access user1's store management pages
        manage_url = reverse('store_manage', kwargs={'pk': self.approved_store.pk})
        update_url = reverse('store_update', kwargs={'pk': self.approved_store.pk})
        add_product_url = reverse('product_create', kwargs={'pk': self.approved_store.pk})

        self.assertEqual(self.client.get(manage_url).status_code, 403)
        self.assertEqual(self.client.get(update_url).status_code, 403)
        self.assertEqual(self.client.get(add_product_url).status_code, 403)

    def test_owner_can_access_management_views(self):
        """The owner of a store should be able to access their management pages."""
        self.client.login(username='user1', password='password123')

        manage_url = reverse('store_manage', kwargs={'pk': self.approved_store.pk})
        update_url = reverse('store_update', kwargs={'pk': self.approved_store.pk})
        add_product_url = reverse('product_create', kwargs={'pk': self.approved_store.pk})

        self.assertEqual(self.client.get(manage_url).status_code, 200)
        self.assertEqual(self.client.get(update_url).status_code, 200)
        self.assertEqual(self.client.get(add_product_url).status_code, 200)

    def test_owner_cannot_add_product_to_pending_store(self):
        """A store owner should get a 403 Forbidden error when trying to add a product to a PENDING store."""
        self.client.login(username='user1', password='password123')
        add_product_url = reverse('product_create', kwargs={'pk': self.pending_store.pk})
        response = self.client.get(add_product_url)
        self.assertEqual(response.status_code, 403)


class StoreViewContentTests(TestCase):
    """
    Tests focused on the content and logic of the views.
    """
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')

        self.store1 = create_store(self.user1, 'Pet Paradise', 'PET', 'APPROVED')
        self.store2 = create_store(self.user1, 'Pending Supplies', 'SUPPLIES', 'PENDING')
        self.store3 = create_store(self.user2, 'Doggy Depot', 'PET', 'APPROVED')

        self.product1 = create_product(self.store1, 'Cat Food', 19.99)
        self.product2 = create_product(self.store3, 'Dog Leash', 25.50)

    def test_my_store_list_view(self):
        """MyStoreListView should only show stores owned by the logged-in user."""
        self.client.login(username='user1', password='password123')
        response = self.client.get(reverse('store_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.store1.name)
        self.assertContains(response, self.store2.name)
        self.assertNotContains(response, self.store3.name)

    def test_marketplace_view_shows_only_approved_products(self):
        """MarketplaceView should only display products from approved stores."""
        # Create a product in a pending store, which should not be visible
        create_product(self.store2, 'Hidden Item', 10.00)
        
        response = self.client.get(reverse('marketplace'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product1.name)
        self.assertContains(response, self.product2.name)
        self.assertNotContains(response, 'Hidden Item')

    def test_marketplace_search_functionality(self):
        """Marketplace search should filter products and find stores."""
        # Search for a product name
        response = self.client.get(reverse('marketplace'), {'q': 'Cat Food'})
        self.assertContains(response, self.product1.name)
        self.assertNotContains(response, self.product2.name)

        # Search for a store name
        response = self.client.get(reverse('marketplace'), {'q': 'Doggy Depot'})
        self.assertContains(response, self.product2.name) # Shows related product
        self.assertContains(response, 'Doggy Depot') # Shows the store itself

    def test_marketplace_filter_by_type(self):
        """Marketplace filter should correctly filter by store type."""
        response = self.client.get(reverse('marketplace'), {'type': 'SUPPLIES'})
        self.assertNotContains(response, self.product1.name)
        self.assertNotContains(response, self.product2.name)

    def test_store_profile_view(self):
        """StoreProfileView should show store details and its products."""
        response = self.client.get(reverse('store_profile', kwargs={'pk': self.store1.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.store1.name)
        self.assertContains(response, self.product1.name)

    def test_store_manage_view_content(self):
        """StoreManageView should show the owner's store details and all its products."""
        self.client.login(username='user1', password='password123')
        response = self.client.get(reverse('store_manage', kwargs={'pk': self.store1.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.store1.name)
        self.assertContains(response, self.product1.name)


class FormSubmissionTests(TestCase):
    """
    Tests focused on creating and updating data via forms.
    """
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.login(username='testuser', password='password123')
        self.approved_store = create_store(self.user, 'My Test Store', 'PET', 'APPROVED')

    def test_store_request_creation(self):
        """A user can successfully submit a form to request a new store."""
        response = self.client.post(reverse('store_request'), {
            'name': 'New Awesome Store',
            'description': 'A great store.',
            'store_type': 'SUPPLIES'
        })
        self.assertRedirects(response, reverse('store_list'))
        self.assertTrue(Store.objects.filter(name='New Awesome Store').exists())
        new_store = Store.objects.get(name='New Awesome Store')
        self.assertEqual(new_store.owner, self.user)
        self.assertEqual(new_store.status, 'PENDING')

    def test_product_creation(self):
        """An owner of an approved store can create a new product."""
        product_count_before = Product.objects.count()
        response = self.client.post(reverse('product_create', kwargs={'pk': self.approved_store.pk}), {
            'name': 'New Product',
            'description': 'A cool new product.',
            'price': 99.99,
            'stock': 10
        })
        self.assertRedirects(response, reverse('store_manage', kwargs={'pk': self.approved_store.pk}))
        self.assertEqual(Product.objects.count(), product_count_before + 1)
        new_product = Product.objects.get(name='New Product')
        self.assertEqual(new_product.store, self.approved_store)

    def test_store_update(self):
        """A store owner can update their store's information."""
        response = self.client.post(reverse('store_update', kwargs={'pk': self.approved_store.pk}), {
            'name': 'My Updated Store Name',
            'description': 'Updated description.'
        })
        self.assertRedirects(response, reverse('store_manage', kwargs={'pk': self.approved_store.pk}))
        
        # Refresh the object from the database to check for changes
        self.approved_store.refresh_from_db()
        self.assertEqual(self.approved_store.name, 'My Updated Store Name')