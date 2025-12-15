from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from app.stores.models import Store, Product, ProductReview, StoreReview
from app.accounts.models import Notification

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

class MarketplaceViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='password')
        
        self.store_pet = Store.objects.create(
            owner=self.user,
            name='Pet Shop A',
            store_type='PET',
            status='APPROVED'
        )
        
        self.store_supplies = Store.objects.create(
            owner=self.user,
            name='Supply Shop B',
            store_type='SUPPLIES',
            status='APPROVED'
        )
        
        self.store_pending = Store.objects.create(
            owner=self.user,
            name='Pending Shop',
            store_type='PET',
            status='PENDING'
        )
        
        self.p1 = Product.objects.create(store=self.store_pet, name='Dog Food', description='Yummy', price=100, stock=10)
        self.p2 = Product.objects.create(store=self.store_supplies, name='Leash', description='Strong', price=50, stock=5)
        self.p3_out_of_stock = Product.objects.create(store=self.store_pet, name='Gone', price=10, stock=0)
        self.p4_pending = Product.objects.create(store=self.store_pending, name='Hidden', price=10, stock=10)

        self.url = reverse('marketplace')

    def test_view_filters_approved_and_stock(self):
        """Show only products from APPROVED stores with stock > 0"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        products = response.context['products']
        
        self.assertIn(self.p1, products)
        self.assertIn(self.p2, products)
        self.assertNotIn(self.p3_out_of_stock, products)
        self.assertNotIn(self.p4_pending, products)      

    def test_search_functionality(self):
        response = self.client.get(self.url, {'q': 'Food'})
        self.assertIn(self.p1, response.context['products'])
        self.assertNotIn(self.p2, response.context['products'])
        
        response = self.client.get(self.url, {'q': 'Strong'})
        self.assertIn(self.p2, response.context['products'])
        
        response = self.client.get(self.url, {'q': 'Supply Shop'})
        self.assertIn(self.p2, response.context['products'])

    def test_filter_by_store_type(self):
        """Filter by PET or SUPPLIES"""
        response = self.client.get(self.url, {'type': 'PET'})
        products = response.context['products']
        self.assertIn(self.p1, products)
        self.assertNotIn(self.p2, products)

    def test_sort_by_price(self):
        """Test price_low and price_high"""

        response = self.client.get(self.url, {'sort': 'price_low'})
        products = list(response.context['products'])
        self.assertEqual(products, [self.p2, self.p1])
        
        response = self.client.get(self.url, {'sort': 'price_high'})
        products = list(response.context['products'])
        self.assertEqual(products, [self.p1, self.p2])

    def test_sort_by_rating(self):
        """Test rating_high logic with annotation"""
        reviewer = User.objects.create_user(username='reviewer', password='password')
        
        ProductReview.objects.create(product=self.p1, author=reviewer, rating=1, comment='Bad')
        ProductReview.objects.create(product=self.p2, author=reviewer, rating=5, comment='Good')
        
        response = self.client.get(self.url, {'sort': 'rating_high'})
        products = list(response.context['products'])
        
        self.assertEqual(products[0], self.p2)
        self.assertEqual(products[1], self.p1)

    def test_pagination(self):
        for i in range(13):
            Product.objects.create(store=self.store_pet, name=f'Extra {i}', price=10, stock=1)
            
        response = self.client.get(self.url)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['products']), 12)

class ProductDetailViewTests(TestCase):
    def setUp(self):
        # 1. สร้าง User (เจ้าของร้าน และ คนรีวิว)
        self.owner = User.objects.create_user(username='owner', password='password')
        self.reviewer = User.objects.create_user(username='reviewer', password='password')
        
        # 2. สร้าง Store (จำเป็นต้องมีเพราะ Product ผูกกับ Store)
        self.store = Store.objects.create(
            owner=self.owner,
            name='Test Store',
            description='Test Desc',
            store_type='PET',
            status='APPROVED'
        )
        
        # 3. สร้าง Product
        self.product = Product.objects.create(
            store=self.store,
            name='Test Product',
            description='Desc',
            price=100.00,
            stock=10
        )
        
        # 4. กำหนด URL (ตรวจสอบว่าใน urls.py ตั้งชื่อ name='product_detail' หรือไม่)
        self.url = reverse('product_detail', kwargs={'pk': self.product.pk})

    def test_view_loads_success_and_context_correct(self):
        # 5. สร้าง Review จำลอง 2 อัน (5 ดาว และ 3 ดาว -> เฉลี่ยต้องได้ 4.0)
        # หมายเหตุ: field 'order' เป็น null=True ดังนั้นไม่ต้องใส่ก็ได้
        ProductReview.objects.create(product=self.product, author=self.reviewer, rating=5, comment='Great')
        ProductReview.objects.create(product=self.product, author=self.owner, rating=3, comment='Okay') # ให้เจ้าของรีวิวเล่นๆ เพื่อเทส

        # 6. ยิง GET Request
        response = self.client.get(self.url)
        
        # 7. ตรวจสอบผลลัพธ์
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'stores/product_detail.html')
        
        # ตรวจสอบว่าสินค้าถูกต้อง
        self.assertEqual(response.context['product'], self.product)
        
        # ตรวจสอบ Rating เฉลี่ย (5+3)/2 = 4.0
        self.assertEqual(response.context['average_rating'], 4.0)
        
        # ตรวจสอบจำนวนรีวิว
        self.assertEqual(len(response.context['reviews']), 2)

class ProductUpdateViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='password')
        self.follower = User.objects.create_user(username='follower', password='password')
        self.stranger = User.objects.create_user(username='stranger', password='password')
        
        self.store = Store.objects.create(
            owner=self.owner,
            name='My Shop',
            description='Test Shop',
            store_type='PET',
            status='APPROVED'
        )
        self.store.followers.add(self.follower)
        
        self.product = Product.objects.create(
            store=self.store,
            name='Original Name',
            description='Desc',
            price=100.00,
            discount_price=None,
            stock=10
        )
        
        self.url = reverse('product_update', kwargs={'pk': self.product.pk})

    def test_view_access_control(self):
        """คนอื่นที่ไม่ใช่เจ้าของร้าน เข้ามาแก้ไม่ได้ (ต้องได้ 404)"""
        self.client.force_login(self.stranger)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_update_triggers_notification_on_new_sale(self):
        """เปลี่ยนจากราคาเต็ม -> ลดราคา ต้องมีการแจ้งเตือน"""
        self.client.force_login(self.owner)
        
        data = {
            'name': 'Original Name',
            'description': 'Desc',
            'price': 100.00,
            'discount_price': 80.00,
            'stock': 10
        }
        
        response = self.client.post(self.url, data)
        
        # 1. เช็ค Redirect
        self.assertRedirects(response, reverse('store_manage', kwargs={'pk': self.store.pk}))
        
        # 2. เช็คข้อมูลเปลี่ยนจริง
        self.product.refresh_from_db()
        self.assertEqual(self.product.discount_price, 80.00)
        
        # 3. เช็ค Notification
        self.assertEqual(Notification.objects.count(), 1)
        noti = Notification.objects.first()
        self.assertEqual(noti.user, self.follower) # ส่งให้ follower
        self.assertIn('SALE -20%', noti.message)   # ข้อความถูกต้อง

    def test_update_no_notification_if_price_same(self):
        """ถ้าลดราคาอยู่แล้ว และอัปเดตอย่างอื่น (แต่ราคาเท่าเดิม) ต้องไม่แจ้งเตือนซ้ำ"""
        # Setup: ลดราคาอยู่แล้ว
        self.product.discount_price = 80.00
        self.product.save()
        
        self.client.force_login(self.owner)
        
        data = {
            'name': 'New Name', # เปลี่ยนชื่อสินค้า
            'description': 'Desc',
            'price': 100.00,
            'discount_price': 80.00, # ราคาเดิม
            'stock': 5
        }
        
        self.client.post(self.url, data)
        
        # ต้องไม่มี Notification ใหม่
        self.assertEqual(Notification.objects.count(), 0)
        
        # แต่ชื่อต้องเปลี่ยน
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'New Name')

    def test_update_triggers_notification_on_deeper_sale(self):
        """ถ้าลดราคาอยู่แล้ว แต่ลดเพิ่มอีก (80 -> 50) ต้องแจ้งเตือนใหม่"""
        self.product.discount_price = 80.00
        self.product.save()
        
        self.client.force_login(self.owner)
        
        data = {
            'name': 'Original Name',
            'description': 'Desc',
            'price': 100.00,
            'discount_price': 50.00, # ลดเพิ่ม!
            'stock': 10
        }
        
        self.client.post(self.url, data)
        
        self.assertEqual(Notification.objects.count(), 1)
        self.assertIn('SALE -50%', Notification.objects.first().message)

    def test_remove_discount_no_notification(self):
        """ถ้าเอาราคาลดออก (เลิกลด) ต้องไม่แจ้งเตือน"""
        self.product.discount_price = 80.00
        self.product.save()
        
        self.client.force_login(self.owner)
        
        data = {
            'name': 'Original Name',
            'description': 'Desc',
            'price': 100.00,
            'discount_price': '', # ลบออก
            'stock': 10
        }
        
        self.client.post(self.url, data)
        
        self.product.refresh_from_db()
        self.assertIsNone(self.product.discount_price)
        self.assertEqual(Notification.objects.count(), 0)

    def test_context_contains_store_object(self):
        """ทดสอบว่าใน Context มีตัวแปร 'store' ส่งไปด้วย"""
        self.client.force_login(self.owner)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('store', response.context)
        self.assertEqual(response.context['store'], self.store)

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

class StoreReviewCreateViewTests(TestCase):
    def setUp(self):
        # 1. สร้าง Users
        self.owner = User.objects.create_user(username='owner', password='password')
        self.reviewer = User.objects.create_user(username='reviewer', password='password')
        
        # 2. สร้าง Store
        self.store = Store.objects.create(
            owner=self.owner,
            name='Test Store',
            description='Desc',
            store_type='PET',
            status='APPROVED'
        )
        
        self.url = reverse('store_review_create', kwargs={'pk': self.store.pk}) 
        self.store_profile_url = reverse('store_profile', kwargs={'pk': self.store.pk})

    def test_create_review_success(self):
        """ทดสอบการสร้างรีวิวสำเร็จ"""
        self.client.force_login(self.reviewer)
        
        data = {
            'rating': 5,
            'comment': 'Excellent service!',
        }
        
        response = self.client.post(self.url, data)
        
        # 1. เช็ค Redirect ไปหน้า Store Profile
        self.assertRedirects(response, self.store_profile_url)
        
        # 2. เช็คข้อมูลลง Database ถูกต้อง
        self.assertEqual(StoreReview.objects.count(), 1)
        review = StoreReview.objects.first()
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, 'Excellent service!')
        self.assertEqual(review.author, self.reviewer)
        self.assertEqual(review.store, self.store)
        
        # 3. เช็ค Success Message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('submitted successfully' in str(m) for m in messages))

    def test_prevent_duplicate_review(self):
        """ทดสอบว่าถ้าเคยรีวิวแล้ว ต้องรีวิวซ้ำไม่ได้ (Logic ใน dispatch)"""
        self.client.force_login(self.reviewer)
        
        # สร้างรีวิวไว้ก่อนแล้ว 1 อัน
        StoreReview.objects.create(
            store=self.store,
            author=self.reviewer,
            rating=4,
            comment='First review'
        )
        
        # พยายามเข้าหน้าเขียนรีวิวอีกครั้ง
        response = self.client.get(self.url)
        
        # ต้องถูก Redirect กลับไปหน้า Profile ทันที
        self.assertRedirects(response, self.store_profile_url)
        
        # ต้องมี Error Message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('already reviewed' in str(m) for m in messages))

    def test_context_data_correct(self):
        """ทดสอบว่า Context ส่งค่าไป Template ถูกต้อง"""
        self.client.force_login(self.reviewer)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['target_object'], self.store)
        self.assertEqual(response.context['review_type'], 'Store')