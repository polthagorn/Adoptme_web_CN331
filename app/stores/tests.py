from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from app.stores.models import Store, Product, ProductReview, StoreReview
from django.core.files.uploadedfile import SimpleUploadedFile

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

class StoreRequestCreateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        # สมมติชื่อ URL ตาม view ที่ให้มา (คุณต้องเช็คใน urls.py ว่าตั้งชื่อว่าอะไร)
        # ถ้ายังไม่มี URL 'store_request' ให้เปลี่ยน string นี้ให้ตรงกับของคุณ
        self.url = reverse('store_request') 
        self.success_url = reverse('store_list')

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(response.status_code, 302) # Redirect to login

    def test_create_store_success_with_statement(self):
        self.client.login(username='testuser', password='password')
        
        # เตรียม Data (ใช้ verification_statement เพื่อให้ผ่าน clean method)
        data = {
            'name': 'My Pet Shop',
            'description': 'Best shop',
            'store_type': 'PET',
            'verification_statement': 'I am real.',
            # fields อื่นๆ เป็น optional หรือมี default
        }
        
        response = self.client.post(self.url, data)
        
        # ตรวจสอบ Redirect หลัง save
        self.assertRedirects(response, self.success_url)
        
        # ตรวจสอบว่า Store ถูกสร้างและ Owner ถูก set ถูกต้อง
        self.assertEqual(Store.objects.count(), 1)
        store = Store.objects.first()
        self.assertEqual(store.owner, self.user)
        self.assertEqual(store.name, 'My Pet Shop')

    def test_create_store_validation_error(self):
        self.client.login(username='testuser', password='password')
        
        data = {
            'name': 'Invalid Shop',
            'description': 'Desc',
            'store_type': 'SUPPLIES',
            'verification_statement': '', 
            'verification_document': ''
        }
        
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Store.objects.exists())
        form_errors = response.context['form'].errors.as_text()
        self.assertIn('must submit at least one', form_errors)

class MarketplaceViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='test', password='password')
        self.url = reverse('marketplace') # เช็คชื่อ URL ใน urls.py

        # 1. Store Approved (Type: PET)
        self.store_pet = Store.objects.create(
            owner=self.user, name="Pet Shop", status='APPROVED', store_type='PET'
        )
        # 2. Store Approved (Type: SUPPLIES)
        self.store_supplies = Store.objects.create(
            owner=self.user, name="Supply Shop", status='APPROVED', store_type='SUPPLIES'
        )
        # 3. Store Pending (Should be hidden)
        self.store_pending = Store.objects.create(
            owner=self.user, name="Pending Shop", status='PENDING', store_type='PET'
        )

        # Products
        self.p_pet = Product.objects.create(store=self.store_pet, name="Dog Food", description="Yummy", price=100)
        self.p_supply = Product.objects.create(store=self.store_supplies, name="Cage", description="Strong", price=500)
        self.p_hidden = Product.objects.create(store=self.store_pending, name="Hidden", price=10)

        # Reviews for Rating Sort
        ProductReview.objects.create(product=self.p_pet, author=self.user, rating=5, comment="Great")
        ProductReview.objects.create(product=self.p_supply, author=self.user, rating=1, comment="Bad")

    def test_marketplace_base_visibility(self):
        # Test Default View (Only Approved Stores)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'stores/marketplace.html')
        
        products = response.context['products']
        self.assertIn(self.p_pet, products)
        self.assertIn(self.p_supply, products)
        self.assertNotIn(self.p_hidden, products) # Pending store excluded

    def test_search_filter(self):
        # Test Search (q=Dog)
        response = self.client.get(self.url, {'q': 'Dog'})
        products = response.context['products']
        
        self.assertIn(self.p_pet, products)
        self.assertNotIn(self.p_supply, products)

    def test_type_filter(self):
        # Test Type Filter (type=SUPPLIES)
        response = self.client.get(self.url, {'type': 'SUPPLIES'})
        products = response.context['products']
        
        self.assertIn(self.p_supply, products)
        self.assertNotIn(self.p_pet, products)

    def test_sort_rating_high(self):
        # Test Sort by Rating (High -> Low)
        response = self.client.get(self.url, {'sort': 'rating_high'})
        products = list(response.context['products'])
        
        # Check annotation & order
        self.assertTrue(hasattr(products[0], 'avg_rating'))
        self.assertEqual(products[0], self.p_pet)    # Rating 5
        self.assertEqual(products[1], self.p_supply) # Rating 1

    def test_sort_price_low(self):
        # Test Sort by Price (Low -> High)
        response = self.client.get(self.url, {'sort': 'price_low'})
        products = list(response.context['products'])
        
        self.assertEqual(products[0], self.p_pet)    
        self.assertEqual(products[1], self.p_supply) 

class ProductDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='test', password='password')
        self.store = Store.objects.create(owner=self.user, name="Shop", status='APPROVED')
        self.product = Product.objects.create(store=self.store, name="Item", price=10)
        ProductReview.objects.create(product=self.product, author=self.user, rating=4, comment="Good")
        self.url = reverse('product_detail', args=[self.product.pk])

    def test_product_detail_coverage(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'stores/product_detail.html')
        self.assertIn('reviews', response.context)
        self.assertEqual(response.context['average_rating'], 4.0)

class ProductUpdateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='password')
        self.other_user = User.objects.create_user(username='other', password='password')
        
        self.store = Store.objects.create(owner=self.user, name='Test Store')  # CHECK_THIS: Add required fields
        self.product = Product.objects.create(
            store=self.store,
            name='Old Name',  # CHECK_THIS: Add required fields
            price=100
        )
        self.url = reverse('product_update', kwargs={'pk': self.product.pk})  # CHECK_THIS: Verify URL name

    def test_view_requires_login(self):
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(response.status_code, 302)

    def test_get_queryset_filters_by_owner(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_context_data_contains_store(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['store'], self.store)
        self.assertTemplateUsed(response, 'stores/product_update_form.html')

class ProductUpdateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='password')
        self.other_user = User.objects.create_user(username='other', password='password')
        
        self.store = Store.objects.create(
            owner=self.user,
            name='Test Store',
            description='Test Store Description',
            store_type='PET',
            status='APPROVED'
        )
        
        self.product = Product.objects.create(
            store=self.store,
            name='Old Name',
            description='Old Description',
            price=100.00,
            stock=10
        )
        self.url = reverse('product_update', kwargs={'pk': self.product.pk}) # CHECK_THIS: Verify URL name

    def test_view_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_get_queryset_filters_by_owner(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_context_data_contains_store(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['store'], self.store)

    def test_update_success_and_redirect(self):
        self.client.force_login(self.user)
        
        new_image = SimpleUploadedFile(
            "test_image.gif",
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b',
            content_type="image/gif"
        )
        
        data = {
            'name': 'New Name',
            'description': 'New Description',
            'price': 200.00,
            'stock': 20,
            'image': new_image
        }
        
        response = self.client.post(self.url, data)
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'New Name')
        self.assertEqual(self.product.price, 200.00)
        self.assertRedirects(response, reverse('store_manage', kwargs={'pk': self.store.pk}))

class ProductDeleteViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='password')
        self.other_user = User.objects.create_user(username='other', password='password')
        
        self.store = Store.objects.create(
            owner=self.user, 
            name='Test Store',
            description='Test Description',
            store_type='PET'
        )
        
        self.product = Product.objects.create(
            store=self.store,
            name='Test Product',
            description='Product Description',
            price=100.00,
            stock=10
        )
        self.url = reverse('product_delete', kwargs={'pk': self.product.pk}) # CHECK_THIS: Verify URL name in urls.py

    def test_delete_view_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_delete_view_queryset_restriction(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_delete_success_and_redirect(self):
        self.client.force_login(self.user)
        
        get_response = self.client.get(self.url)
        self.assertEqual(get_response.status_code, 200)
        self.assertTemplateUsed(get_response, 'stores/product_confirm_delete.html')
        
        post_response = self.client.post(self.url)
        
        self.assertRedirects(post_response, reverse('store_manage', kwargs={'pk': self.store.pk}))
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

class StoreReviewListViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='password')
        self.reviewer = User.objects.create_user(username='reviewer', password='password')
        
        self.store = Store.objects.create(
            owner=self.owner,
            name='Test Store',
            description='Store Description',
            store_type='PET',
            status='APPROVED'
        )
        
        self.review1 = StoreReview.objects.create(
            store=self.store,
            author=self.reviewer,
            rating=5,
            comment='Great store!'
        )
        
        self.url = reverse('store_review_list', kwargs={'pk': self.store.pk}) # CHECK_THIS: Verify URL name

    def test_view_status_code(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'stores/store_review_list.html')

    def test_context_contains_reviews(self):
        response = self.client.get(self.url)
        self.assertIn('store', response.context)
        self.assertIn('reviews', response.context)
        
        self.assertEqual(response.context['store'], self.store)
        self.assertIn(self.review1, response.context['reviews'])
        self.assertEqual(len(response.context['reviews']), 1)

    def test_view_returns_404_for_invalid_store(self):
        url = reverse('store_review_list', kwargs={'pk': 9999}) # CHECK_THIS: Verify URL name
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)