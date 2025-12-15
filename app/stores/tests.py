import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from app.stores.models import Store, Product, ProductReview, StoreReview, Order, Cart, CartItem, Payment, OrderItem
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

class ProductReviewListViewTests(TestCase):
    def setUp(self):
        # 1. สร้าง Data จำลอง
        self.owner = User.objects.create_user(username='owner', password='password')
        self.user1 = User.objects.create_user(username='user1', password='password')
        self.user2 = User.objects.create_user(username='user2', password='password')
        
        self.store = Store.objects.create(
            owner=self.owner, name='Test Shop', store_type='PET', status='APPROVED'
        )
        self.product = Product.objects.create(
            store=self.store, name='Test Product', price=100, stock=10
        )
        
        # 2. สร้างรีวิว 2 อัน (จากคนละ User)
        ProductReview.objects.create(product=self.product, author=self.user1, rating=5, comment='Good')
        ProductReview.objects.create(product=self.product, author=self.user2, rating=4, comment='Nice')

        # CHECK_THIS: ตรวจสอบชื่อ URL ใน urls.py ว่าตั้งชื่อนี้หรือไม่
        self.url = reverse('product_review_list', kwargs={'pk': self.product.pk})

    def test_view_displays_reviews_correctly(self):
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'stores/product_review_list.html')
        
        # ตรวจสอบว่าส่ง reviews มาครบ 2 อัน
        self.assertEqual(len(response.context['reviews']), 2)
        
        # ตรวจสอบว่าส่ง product object มาถูกตัว
        self.assertEqual(response.context['product'], self.product)

class ProductReviewCreateViewTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='password')
        self.owner = User.objects.create_user(username='owner', password='password')
        
        self.store = Store.objects.create(
            owner=self.owner, name='Test Shop', store_type='PET', status='APPROVED'
        )
        self.product = Product.objects.create(
            store=self.store, name='Test Product', price=100, stock=10
        )
        
        self.order = Order.objects.create(
            user=self.buyer,
            store=self.store,
            total_price=100.00,
            status='COMPLETED'
        )
        
        self.url = reverse('product_review_create', kwargs={
            'pk': self.product.pk, 
            'order_id': self.order.pk
        })
        self.order_detail_url = reverse('my_order_detail', kwargs={'pk': self.order.pk})

    def test_create_review_success_with_order_link(self):
        self.client.force_login(self.buyer)
        
        data = {
            'rating': 5,
            'comment': 'Fast delivery!',
        }
        
        response = self.client.post(self.url, data)
        
        self.assertRedirects(response, self.order_detail_url)
        
        review = ProductReview.objects.first()
        self.assertIsNotNone(review)
        self.assertEqual(review.product, self.product)
        self.assertEqual(review.author, self.buyer)
        self.assertEqual(review.order, self.order)
        self.assertEqual(review.comment, 'Fast delivery!')

    def test_prevent_duplicate_review_for_same_order(self):
        self.client.force_login(self.buyer)
        
        ProductReview.objects.create(
            product=self.product,
            author=self.buyer,
            order=self.order,
            rating=4,
            comment='First review'
        )
        
        response = self.client.get(self.url)
        
        self.assertRedirects(response, self.order_detail_url)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('already reviewed' in str(m) for m in messages))

    def test_context_data_correct(self):
        """ทดสอบ Context Data"""
        self.client.force_login(self.buyer)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['target_object'], self.product)
        self.assertEqual(response.context['review_type'], 'Product')

class AddToCartViewTests(TestCase):
    def setUp(self):
        # 1. สร้าง User
        self.user = User.objects.create_user(username='buyer', password='password')
        self.owner = User.objects.create_user(username='owner', password='password')
        
        # 2. สร้าง Store & Product
        self.store = Store.objects.create(
            owner=self.owner, name='Shop', store_type='PET', status='APPROVED'
        )
        self.product = Product.objects.create(
            store=self.store, name='Test Item', price=100, stock=5
        )
        
        # URL (เช็คชื่อใน urls.py)
        self.url = reverse('add_to_cart', kwargs={'pk': self.product.pk})
        self.detail_url = reverse('product_detail', kwargs={'pk': self.product.pk})

    def test_add_new_item_to_cart_success(self):
        """เพิ่มสินค้าใหม่ลงตะกร้า"""
        self.client.force_login(self.user)
        
        response = self.client.post(self.url, {'quantity': 2})
        
        # เช็ค Redirect กลับหน้าเดิม
        self.assertRedirects(response, self.detail_url)
        
        # เช็ค Database
        cart_item = CartItem.objects.filter(cart__user=self.user, product=self.product).first()
        self.assertIsNotNone(cart_item)
        self.assertEqual(cart_item.quantity, 2)
        
        # เช็ค Message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Added' in str(m) for m in messages))

    def test_add_existing_item_accumulates_quantity(self):
        """เพิ่มสินค้าเดิม จำนวนต้องบวกเพิ่ม"""
        self.client.force_login(self.user)
        
        # มีของเดิมอยู่แล้ว 1 ชิ้น
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        
        # เพิ่มอีก 2 ชิ้น
        self.client.post(self.url, {'quantity': 2})
        
        item = CartItem.objects.get(cart=cart, product=self.product)
        self.assertEqual(item.quantity, 3) # 1 + 2 = 3

    def test_cannot_add_more_than_stock_new_item(self):
        """เทสกรณีขอซื้อมากกว่าสต็อก (สินค้าใหม่)"""
        self.client.force_login(self.user)
        
        # Stock มี 5 ขอซื้อ 10
        response = self.client.post(self.url, {'quantity': 10})
        
        self.assertRedirects(response, self.detail_url)
        
        # ตะกร้าต้องว่างเปล่า
        self.assertFalse(CartItem.objects.filter(cart__user=self.user).exists())
        
        # เช็ค Error Message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('items left' in str(m) for m in messages))

    def test_cannot_add_more_than_stock_existing_item(self):
        """เทสกรณีมีของในตะกร้าแล้ว พอรวมกับของใหม่เกินสต็อก"""
        self.client.force_login(self.user)
        
        cart = Cart.objects.create(user=self.user)
        # มีในตะกร้า 3 (Stock 5)
        item = CartItem.objects.create(cart=cart, product=self.product, quantity=3)
        
        # ขอเพิ่มอีก 3 (รวมเป็น 6 เกินสต็อก)
        response = self.client.post(self.url, {'quantity': 3})
        
        self.assertRedirects(response, self.detail_url)
        
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3) # ต้องเท่าเดิม ห้ามเพิ่ม
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Cannot add more' in str(m) for m in messages))

class UpdateCartQuantityViewTests(TestCase):
    def setUp(self):
        # 1. Setup User & Store
        self.user = User.objects.create_user(username='buyer', password='password')
        self.store = Store.objects.create(owner=User.objects.create(username='owner'), name='Shop', status='APPROVED')
        
        # 2. Setup Product (Stock = 5, Price = 100)
        self.product = Product.objects.create(store=self.store, name='Item', price=100.00, stock=5)
        
        # 3. Setup Cart & Item (Start with Qty = 1)
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart, 
            product=self.product, 
            quantity=1, 
            is_selected=True # สำคัญ: เพราะ View คำนวณยอดเฉพาะที่ selected
        )
        
        self.url = reverse('update_cart_quantity', kwargs={'pk': self.cart_item.pk})

    def test_increase_quantity_success(self):
        """ทดสอบเพิ่มจำนวนจาก 1 -> 2"""
        self.client.force_login(self.user)
        
        data = {'action': 'increase'}
        response = self.client.post(self.url, json.dumps(data), content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        res_json = response.json()
        
        self.assertTrue(res_json['success'])
        self.assertEqual(res_json['item_quantity'], 2)
        self.assertEqual(res_json['item_total'], 200.0)
        
        self.cart_item.refresh_from_db()
        self.assertEqual(self.cart_item.quantity, 2)

    def test_decrease_quantity_success(self):
        self.cart_item.quantity = 2
        self.cart_item.save()
        
        self.client.force_login(self.user)
        data = {'action': 'decrease'}
        response = self.client.post(self.url, json.dumps(data), content_type='application/json')
        
        res_json = response.json()
        self.assertTrue(res_json['success'])
        self.assertEqual(res_json['item_quantity'], 1)
        self.assertEqual(res_json['item_total'], 100.0)

    def test_increase_fails_if_stock_limit_reached(self):
        self.cart_item.quantity = 5
        self.cart_item.save()
        
        self.client.force_login(self.user)
        data = {'action': 'increase'}
        response = self.client.post(self.url, json.dumps(data), content_type='application/json')
        
        res_json = response.json()
        self.assertFalse(res_json['success'])
        self.assertEqual(res_json['error'], 'Max stock reached')
        
        self.cart_item.refresh_from_db()
        self.assertEqual(self.cart_item.quantity, 5)

    def test_decrease_fails_if_quantity_is_one(self):
        self.client.force_login(self.user)
        data = {'action': 'decrease'}
        response = self.client.post(self.url, json.dumps(data), content_type='application/json')
        
        res_json = response.json()
        self.assertFalse(res_json['success'])
        self.assertEqual(res_json['error'], 'Minimum quantity is 1')

    def test_cannot_update_other_user_item(self):
        other_user = User.objects.create_user(username='thief', password='password')
        self.client.force_login(other_user)
        
        data = {'action': 'increase'}
        response = self.client.post(self.url, json.dumps(data), content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        res_json = response.json()
        self.assertFalse(res_json['success'])

class CartDetailViewTests(TestCase):
    def setUp(self):
        # 1. สร้าง User
        self.buyer = User.objects.create_user(username='buyer', password='password')
        self.owner = User.objects.create_user(username='owner', password='password')
        
        # 2. สร้างร้านค้า 2 ประเภท (PET และ SUPPLIES)
        self.pet_store = Store.objects.create(
            owner=self.owner, name='Pet Shop A', store_type='PET', status='APPROVED'
        )
        self.supply_store = Store.objects.create(
            owner=self.owner, name='Supply Shop B', store_type='SUPPLIES', status='APPROVED'
        )
        
        # 3. สร้างสินค้า
        self.dog_food = Product.objects.create(store=self.pet_store, name='Dog Food', price=100, stock=10)
        self.shampoo = Product.objects.create(store=self.supply_store, name='Shampoo', price=50, stock=10)
        
        # 4. สร้างตะกร้าสินค้า
        self.cart = Cart.objects.create(user=self.buyer)
        
        # URL (สมมติชื่อ 'cart_detail')
        self.url = reverse('cart_detail')

    def test_cart_grouping_logic(self):
        """ทดสอบการแยกประเภทและจัดกลุ่มร้านค้า"""
        # เพิ่มของลงตะกร้า (ทั้ง Pet และ Supplies)
        CartItem.objects.create(cart=self.cart, product=self.dog_food, quantity=1, is_selected=True)
        CartItem.objects.create(cart=self.cart, product=self.shampoo, quantity=1, is_selected=True)
        
        self.client.force_login(self.buyer)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'stores/cart_detail.html')
        
        # 1. เช็คว่า Pet Store อยู่ใน grouped_pets
        # grouped_pets เป็น dict_items [(store, [items]), ...]
        grouped_pets = list(response.context['grouped_pets'])
        self.assertEqual(len(grouped_pets), 1)
        self.assertEqual(grouped_pets[0][0], self.pet_store) # Key คือร้านค้า
        self.assertEqual(grouped_pets[0][1][0].product, self.dog_food) # Value คือรายการสินค้า
        
        # 2. เช็คว่า Supply Store อยู่ใน grouped_supplies
        grouped_supplies = list(response.context['grouped_supplies'])
        self.assertEqual(len(grouped_supplies), 1)
        self.assertEqual(grouped_supplies[0][0], self.supply_store)
        self.assertEqual(grouped_supplies[0][1][0].product, self.shampoo)

    def test_calculation_ignores_unselected_items(self):
        """ทดสอบการคำนวณเงิน ต้องไม่รวมรายการที่ไม่ได้เลือก"""
        # Item 1: เลือก (100 x 2 = 200)
        CartItem.objects.create(cart=self.cart, product=self.dog_food, quantity=2, is_selected=True)
        
        # Item 2: ไม่เลือก (50 x 1 = 50) -> ต้องไม่ถูกนำมาคิดเงิน
        CartItem.objects.create(cart=self.cart, product=self.shampoo, quantity=1, is_selected=False)
        
        self.client.force_login(self.buyer)
        response = self.client.get(self.url)
        
        # เช็ค Total: ต้องได้แค่ 200 (ไม่ใช่ 250)
        self.assertEqual(response.context['selected_total'], 200.0)
        
        # เช็ค Count: ต้องได้แค่ 2 ชิ้น (ไม่ใช่ 3)
        self.assertEqual(response.context['selected_count'], 2)

    def test_empty_cart_loads_successfully(self):
        """ทดสอบกรณีตะกร้าว่าง ต้องไม่ Error"""
        self.client.force_login(self.buyer)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_total'], 0)
        self.assertEqual(len(list(response.context['grouped_pets'])), 0)

class ToggleCartItemViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='password')
        self.store = Store.objects.create(owner=User.objects.create(username='owner'), name='Shop', status='APPROVED')
        self.product1 = Product.objects.create(store=self.store, name='Item 1', price=100.00, stock=10)
        self.product2 = Product.objects.create(store=self.store, name='Item 2', price=50.00, stock=10)
        
        self.cart = Cart.objects.create(user=self.user)
        
        # Item 1: ราคา 100 x 1 (Selected = True)
        self.item1 = CartItem.objects.create(cart=self.cart, product=self.product1, quantity=1, is_selected=True)
        
        # Item 2: ราคา 50 x 2 = 100 (Selected = True)
        self.item2 = CartItem.objects.create(cart=self.cart, product=self.product2, quantity=2, is_selected=True)
        
        # ตอนนี้รวมทั้งตะกร้าคือ 200 บาท
        
        self.url = reverse('toggle_cart_item', kwargs={'pk': self.item1.pk})

    def test_unselect_item_updates_total_correctly(self):
        """ทดสอบการติ๊กออก (Unselect) -> ยอดรวมต้องลดลง"""
        self.client.force_login(self.user)
        
        data = {'is_selected': False} # ติ๊กออก
        response = self.client.post(self.url, json.dumps(data), content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        res_json = response.json()
        
        self.assertTrue(res_json['success'])
        
        # Item 1 (100) ถูกเอาออก -> เหลือแค่ Item 2 (100)
        self.assertEqual(res_json['new_total'], 100.0)
        self.assertEqual(res_json['new_count'], 2) # เหลือจำนวนชิ้นแค่ของ Item 2
        
        # เช็ค Database
        self.item1.refresh_from_db()
        self.assertFalse(self.item1.is_selected)

    def test_select_item_updates_total_correctly(self):
        """ทดสอบการติ๊กเข้า (Select) -> ยอดรวมต้องเพิ่มขึ้น"""
        # Set ให้ Item 1 ไม่ได้เลือกไว้ก่อน
        self.item1.is_selected = False
        self.item1.save()
        
        self.client.force_login(self.user)
        
        data = {'is_selected': True} # ติ๊กเข้า
        response = self.client.post(self.url, json.dumps(data), content_type='application/json')
        
        res_json = response.json()
        
        # กลับมารวมกันเป็น 200 (Item 1 + Item 2)
        self.assertEqual(res_json['new_total'], 200.0)
        self.assertEqual(res_json['new_count'], 3) # 1 + 2 ชิ้น
        
        self.item1.refresh_from_db()
        self.assertTrue(self.item1.is_selected)

    def test_toggle_other_user_item_fails(self):
        """คนอื่นห้ามมา toggle ของเรา (View catch error -> return 400)"""
        other_user = User.objects.create_user(username='thief', password='password')
        self.client.force_login(other_user)
        
        data = {'is_selected': False}
        response = self.client.post(self.url, json.dumps(data), content_type='application/json')
        
        # View ใช้ try...except ครอบ get_object_or_404 ไว้ จึงได้ 400
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])

class RemoveFromCartTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password')
        store = Store.objects.create(owner=self.user, name='Shop', store_type='PET')
        product = Product.objects.create(store=store, name='Item', price=10)
        
        self.cart = Cart.objects.create(user=self.user)
        self.item = CartItem.objects.create(cart=self.cart, product=product, quantity=1)
        
        self.url = reverse('remove_from_cart', kwargs={'pk': self.item.pk})

    def test_remove_item_success(self):
        self.client.force_login(self.user)
        
        # ยิง Request (ใช้ POST หรือ GET ก็ได้ตามที่ html ส่งมา)
        response = self.client.post(self.url)
        
        # 1. เช็ค Redirect
        self.assertRedirects(response, reverse('cart_detail'))
        
        # 2. เช็คว่าของหายไปจาก DB
        self.assertFalse(CartItem.objects.filter(pk=self.item.pk).exists())

class CheckoutViewTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='password')
        self.seller_a = User.objects.create_user(username='seller_a', password='password')
        self.seller_b = User.objects.create_user(username='seller_b', password='password')

        self.store_a = Store.objects.create(owner=self.seller_a, name='Shop A', status='APPROVED')
        self.store_b = Store.objects.create(owner=self.seller_b, name='Shop B', status='APPROVED')

        self.prod_a = Product.objects.create(store=self.store_a, name='Item A', price=100, stock=10)
        self.prod_b = Product.objects.create(store=self.store_b, name='Item B', price=50, stock=10)

        self.cart = Cart.objects.create(user=self.buyer)

        self.item_a = CartItem.objects.create(cart=self.cart, product=self.prod_a, quantity=2, is_selected=True)
        self.item_b = CartItem.objects.create(cart=self.cart, product=self.prod_b, quantity=1, is_selected=True)

        self.prod_a_2 = Product.objects.create(store=self.store_a, name='Item A2', price=20, stock=5)
        self.item_unselected = CartItem.objects.create(cart=self.cart, product=self.prod_a_2, quantity=1, is_selected=False)

        self.url = reverse('checkout')

    def test_checkout_success_split_orders_and_deduct_stock(self):
        self.client.force_login(self.buyer)
        response = self.client.get(self.url)

        self.assertRedirects(response, reverse('my_order_list'))
        self.assertEqual(Order.objects.count(), 2)

        order_a = Order.objects.get(store=self.store_a)
        order_b = Order.objects.get(store=self.store_b)

        self.assertEqual(order_a.total_price, 200.0)
        self.assertEqual(order_b.total_price, 50.0)

        self.prod_a.refresh_from_db()
        self.prod_b.refresh_from_db()
        self.assertEqual(self.prod_a.stock, 8)
        self.assertEqual(self.prod_b.stock, 9)

        self.assertFalse(CartItem.objects.filter(pk=self.item_a.pk).exists())
        self.assertFalse(CartItem.objects.filter(pk=self.item_b.pk).exists())
        self.assertTrue(CartItem.objects.filter(pk=self.item_unselected.pk).exists())

        noti_a = Notification.objects.filter(user=self.seller_a).first()
        self.assertIsNotNone(noti_a)
        self.assertIn(f"New order #{order_a.id}", noti_a.message)

        noti_b = Notification.objects.filter(user=self.seller_b).first()
        self.assertIsNotNone(noti_b)
        self.assertIn(f"New order #{order_b.id}", noti_b.message)

    def test_checkout_fails_if_out_of_stock(self):
        self.prod_a.stock = 1
        self.prod_a.save()

        self.client.force_login(self.buyer)
        response = self.client.get(self.url)

        self.assertRedirects(response, reverse('cart_detail'))
        self.assertEqual(Order.objects.count(), 0)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('has only 1 left' in str(m) for m in messages))

    def test_checkout_fails_if_no_item_selected(self):
        self.item_a.is_selected = False
        self.item_a.save()
        self.item_b.is_selected = False
        self.item_b.save()

        self.client.force_login(self.buyer)
        response = self.client.get(self.url)

        self.assertRedirects(response, reverse('cart_detail'))
        self.assertEqual(Order.objects.count(), 0)

class OrderPaymentViewTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='password')
        self.seller = User.objects.create_user(username='seller', password='password')
        self.store = Store.objects.create(owner=self.seller, name='Shop', status='APPROVED')
        self.order = Order.objects.create(
            user=self.buyer,
            store=self.store,
            total_price=100.00,
            status='PENDING'
        )
        self.url = reverse('order_payment', kwargs={'pk': self.order.pk})

    def test_get_payment_page_initial_data(self):
        self.client.force_login(self.buyer)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'stores/order_payment.html')
        self.assertEqual(response.context['form'].initial['amount'], 100.00)

    def test_post_payment_success_updates_order_and_notifies(self):
        self.client.force_login(self.buyer)

        # ✅ แก้จุดที่ 1: สร้างไฟล์รูปภาพจำลองที่ถูกต้อง (Valid Image Bytes)
        # นี่คือ Binary code ของรูป GIF ขนาด 1x1 pixel (เพื่อให้ ImageField ยอมรับว่านี่คือรูปจริง)
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )
        image = SimpleUploadedFile("slip.gif", small_gif, content_type="image/gif")

        # ✅ แก้จุดที่ 2: ระบุ format วันที่ให้ชัดเจน (YYYY-MM-DD) ตามมาตรฐาน Django
        data = {
            'amount': 100.00,
            'transfer_date': '2025-01-01', 
            'transfer_time': '12:00',      
            'slip_image': image
        }

        response = self.client.post(self.url, data)

        # ตรวจสอบการ Redirect (302)
        self.assertRedirects(response, reverse('my_order_list'))

        # ตรวจสอบว่าข้อมูลถูกบันทึกจริง
        self.assertTrue(Payment.objects.filter(order=self.order).exists())
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'PAID')

        # ตรวจสอบ Notification
        noti = Notification.objects.filter(user=self.seller).first()
        self.assertIsNotNone(noti)
        self.assertIn(f"Order #{self.order.id}", noti.message)

    def test_cannot_pay_for_other_user_order(self):
        other_user = User.objects.create_user(username='other', password='password')
        self.client.force_login(other_user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

class StoreOrderListViewTests(TestCase):
    def setUp(self):
        # 1. สร้าง Users (เจ้าของร้านเรา, เจ้าของร้านอื่น, ลูกค้า)
        self.my_user = User.objects.create_user(username='me', password='password')
        self.other_user = User.objects.create_user(username='other', password='password')
        self.customer = User.objects.create_user(username='customer', password='password')
        
        # 2. สร้าง Store ของเรา และ ของคนอื่น
        self.my_store = Store.objects.create(owner=self.my_user, name='My Store', status='APPROVED')
        self.other_store = Store.objects.create(owner=self.other_user, name='Other Store', status='APPROVED')
        
        # 3. สร้าง Orders (จำลองสถานการณ์)
        # - ออเดอร์ร้านเรา: รอจ่าย (PENDING)
        self.order_pending = Order.objects.create(
            user=self.customer, store=self.my_store, total_price=100, status='PENDING'
        )
        # - ออเดอร์ร้านเรา: จ่ายแล้ว (PAID)
        self.order_paid = Order.objects.create(
            user=self.customer, store=self.my_store, total_price=200, status='PAID'
        )
        # - ออเดอร์ร้านคนอื่น (ต้องไม่โผล่มาให้เราเห็น)
        self.order_other = Order.objects.create(
            user=self.customer, store=self.other_store, total_price=50, status='PAID'
        )
        
        # CHECK_THIS: ตรวจสอบชื่อ URL ใน urls.py ของคุณ
        self.url = reverse('store_order_list') 

    def test_view_shows_only_my_store_orders(self):
        """ทดสอบว่าเห็นเฉพาะออเดอร์ของร้านตัวเอง (ไม่เห็นของร้านอื่น)"""
        self.client.force_login(self.my_user)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        orders = response.context['orders']
        
        # ต้องมี 2 ออเดอร์ของร้านเรา
        self.assertEqual(len(orders), 2)
        self.assertIn(self.order_pending, orders)
        self.assertIn(self.order_paid, orders)
        
        # ต้องไม่มีออเดอร์ร้านคนอื่น
        self.assertNotIn(self.order_other, orders)

    def test_filter_by_status(self):
        """ทดสอบการกรอง status เช่น ?status=PAID"""
        self.client.force_login(self.my_user)
        
        # ส่ง Query Param ?status=PAID
        response = self.client.get(self.url, {'status': 'PAID'})
        
        orders = response.context['orders']
        
        # ต้องเจอแค่ออเดอร์ที่จ่ายแล้ว
        self.assertEqual(len(orders), 1)
        self.assertIn(self.order_paid, orders)
        self.assertNotIn(self.order_pending, orders)
        
        # เช็ค Context variable สำหรับทำปุ่ม Active
        self.assertEqual(response.context['current_status'], 'PAID')

    def test_filter_all_shows_everything(self):
        """ทดสอบ ?status=ALL หรือไม่ส่งค่ามาเลย"""
        self.client.force_login(self.my_user)
        
        # กรณีส่ง ALL
        response = self.client.get(self.url, {'status': 'ALL'})
        self.assertEqual(len(response.context['orders']), 2)
        
        # กรณีไม่ส่งอะไรเลย
        response = self.client.get(self.url)
        self.assertEqual(len(response.context['orders']), 2)
        self.assertEqual(response.context['current_status'], 'ALL')

class StoreOrderManageViewTests(TestCase):
    def setUp(self):
        # 1. Setup Users
        self.seller = User.objects.create_user(username='seller', password='password')
        self.buyer = User.objects.create_user(username='buyer', password='password')
        self.stranger = User.objects.create_user(username='stranger', password='password')

        # 2. Setup Store & Order
        self.store = Store.objects.create(owner=self.seller, name='My Shop', status='APPROVED')
        self.order = Order.objects.create(
            user=self.buyer,
            store=self.store,
            total_price=100.00,
            status='PAID' # เริ่มต้นที่สถานะจ่ายเงินแล้ว
        )
        
        self.url = reverse('store_order_manage', kwargs={'pk': self.order.pk})

    def test_update_status_confirms_order_and_sends_notification(self):
        """ทดสอบเปลี่ยนสถานะจาก PAID -> CONFIRMED (ต้องส่ง Notification)"""
        self.client.force_login(self.seller)
        
        data = {
            'status': 'CONFIRMED',
            'tracking_number': '',
        }
        
        self.client.post(self.url, data)
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'CONFIRMED')
        
        noti = Notification.objects.filter(user=self.buyer).first()
        self.assertIsNotNone(noti)
        
        # ✅ แก้ตรงนี้: ใช้คำว่า 'Payment Confirmed' ตาม Error log
        self.assertIn('Payment Confirmed', noti.message) 

    def test_update_status_shipped_sends_tracking_notification(self):
        """ทดสอบเปลี่ยนสถานะเป็น SHIPPED (ต้องส่ง Tracking ใน Notification)"""
        self.order.status = 'CONFIRMED'
        self.order.save()
        
        self.client.force_login(self.seller)
        
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )
        image = SimpleUploadedFile("proof.gif", small_gif, content_type="image/gif")
        
        data = {
            'status': 'SHIPPED',
            'tracking_number': 'KERRY-1234',
            'shipping_proof': image
        }
        
        self.client.post(self.url, data)
        
        noti = Notification.objects.filter(user=self.buyer).last()
        
        # ✅ แก้ตรงนี้: ใช้คำว่า 'Shipped' (ตัวพิมพ์เล็กตาม display text)
        self.assertIn('Shipped', noti.message) 
        self.assertIn('Tracking: KERRY-1234', noti.message)

    def test_no_notification_if_status_unchanged(self):
        """ทดสอบกด Save โดยไม่เปลี่ยนสถานะ (ต้องไม่ส่ง Notification ซ้ำ)"""
        self.client.force_login(self.seller)
        
        data = {
            'status': 'PAID',
        }
        
        self.client.post(self.url, data)
        
        self.assertEqual(Notification.objects.count(), 0)

    def test_stranger_cannot_manage_order(self):
        """คนอื่นเข้าหน้านี้ไม่ได้ (404)"""
        self.client.force_login(self.stranger)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_get_manage_page_renders_correctly(self):
        """ทดสอบการเข้าหน้าจัดการออเดอร์ (GET Request)"""
        self.client.force_login(self.seller)
        
        response = self.client.get(self.url)
        
        # 1. ต้องโหลดหน้าเว็บสำเร็จ (Status 200)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'stores/store_order_manage.html')
        
        # 2. ต้องมี 'order' และ 'form' ส่งไปที่ Template
        self.assertIn('order', response.context)
        self.assertIn('form', response.context)
        
        # 3. Form ต้องถูก Bind กับ Order ตัวนี้ (มีข้อมูลเดิมโชว์อยู่)
        form = response.context['form']
        self.assertEqual(form.instance, self.order)
        self.assertEqual(response.context['order'], self.order)

    def test_get_manage_page_404_for_other_store_orders(self):
        """ทดสอบว่าเจ้าของร้าน A จะไปจัดการออเดอร์ของร้าน B ไม่ได้"""
        # สร้างร้านและออเดอร์ของคนอื่น
        other_seller = User.objects.create_user(username='other_seller', password='password')
        other_store = Store.objects.create(owner=other_seller, name='Other Shop', status='APPROVED')
        other_order = Order.objects.create(user=self.buyer, store=other_store, total_price=50, status='PAID')
        
        other_url = reverse('store_order_manage', kwargs={'pk': other_order.pk})
        
        self.client.force_login(self.seller) # เราเป็น Seller A
        
        response = self.client.get(other_url) # พยายามเข้าหน้าจัดการของร้าน B
        
        # ต้องไม่เจอ (404) เพราะ query store__owner=request.user ดักไว้
        self.assertEqual(response.status_code, 404)

class MyOrderDetailViewTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='password')
        self.seller = User.objects.create_user(username='seller', password='password')
        self.other_user = User.objects.create_user(username='other', password='password')

        self.store = Store.objects.create(owner=self.seller, name='Shop', status='APPROVED')
        self.product = Product.objects.create(store=self.store, name='Item', price=100, stock=8)

        self.order_pending = Order.objects.create(
            user=self.buyer, store=self.store, total_price=200, status='PENDING'
        )
        OrderItem.objects.create(
            order=self.order_pending, product=self.product, quantity=2, price=100
        )

        self.order_shipped = Order.objects.create(
            user=self.buyer, store=self.store, total_price=100, status='SHIPPED'
        )

        self.url_pending = reverse('my_order_detail', kwargs={'pk': self.order_pending.pk})
        self.url_shipped = reverse('my_order_detail', kwargs={'pk': self.order_shipped.pk})

    def test_view_permission(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self.url_pending)
        self.assertEqual(response.status_code, 404)

        self.client.force_login(self.buyer)
        response = self.client.get(self.url_pending)
        self.assertEqual(response.status_code, 200)

    def test_cancel_order_restores_stock(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.product.stock, 8)

        response = self.client.post(self.url_pending, {'action': 'cancel'})
        
        self.assertRedirects(response, self.url_pending)
        
        self.order_pending.refresh_from_db()
        self.assertEqual(self.order_pending.status, 'CANCELLED')
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Order cancelled' in str(m) for m in messages))

    def test_receive_order_completes_and_notifies_seller(self):
        self.client.force_login(self.buyer)
        
        response = self.client.post(self.url_shipped, {'action': 'receive'})
        
        self.assertRedirects(response, self.url_shipped)
        
        self.order_shipped.refresh_from_db()
        self.assertEqual(self.order_shipped.status, 'COMPLETED')
        
        noti = Notification.objects.filter(user=self.seller).first()
        self.assertIsNotNone(noti)
        self.assertIn('received by the customer', noti.message)
        self.assertIn(f"Order #{self.order_shipped.id}", noti.message)

    def test_cannot_cancel_if_not_pending(self):
        self.order_pending.status = 'PAID'
        self.order_pending.save()
        
        self.client.force_login(self.buyer)
        
        self.client.post(self.url_pending, {'action': 'cancel'})
        
        self.order_pending.refresh_from_db()
        self.assertEqual(self.order_pending.status, 'PAID')

class ToggleFollowStoreViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password')
        self.owner = User.objects.create_user(username='owner', password='password')
        self.store = Store.objects.create(owner=self.owner, name='Shop', status='APPROVED')
        self.url = reverse('toggle_follow_store', kwargs={'pk': self.store.pk})

    def test_follow_store_success_and_creates_notification(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['following'])
        self.assertEqual(data['count'], 1)

        self.store.refresh_from_db()
        self.assertEqual(self.store.followers.count(), 1)

        noti = Notification.objects.filter(user=self.owner).first()
        self.assertIsNotNone(noti)
        self.assertIn('started following', noti.message)

    def test_unfollow_store_success(self):
        self.store.followers.add(self.user)
        self.client.force_login(self.user)
        
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['following'])
        self.assertEqual(data['count'], 0)

        self.store.refresh_from_db()
        self.assertEqual(self.store.followers.count(), 0)

    def test_owner_follow_own_store_does_not_create_notification(self):
        self.client.force_login(self.owner)
        self.client.post(self.url)

        self.assertEqual(Notification.objects.count(), 0)

class FollowingListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password')
        self.store = Store.objects.create(owner=User.objects.create(username='owner'), name='Shop', status='APPROVED')
        
        self.store.followers.add(self.user)
        
        self.url = reverse('following_list')

    def test_view_context_contains_followed_stores(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'stores/following_list.html')
        
        self.assertIn(self.store, response.context['stores'])
        self.assertEqual(response.context['current_tab'], 'stores')

    def test_tab_parameter_changes_context(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url, {'tab': 'shelters'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_tab'], 'shelters')

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)

    def test_shelters_fallback_to_empty_list_when_missing_relation(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        
        shelters = response.context['shelters']
        
        self.assertEqual(list(shelters), [])