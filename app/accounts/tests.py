from django.test import TestCase, Client, override_settings 
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from app.accounts.models import Profile
from app.accounts.models import Notification
from app.accounts.forms import UserUpdateForm, ProfileUpdateForm
from app.posts.models import Post
import shutil
import tempfile

class AuthViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="old",
            email="old@example.com",
            password="12345"
        )
        Profile.objects.create(user=self.user, phone="111", country="TH", city="Bangkok")

    # ---------------------------
    # LOGIN
    # ---------------------------
    def test_login_happy_path_with_username(self):
        response = self.client.post(reverse('login'), {
            "username_or_email": "old",
            "password": "12345"
        })
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_login_happy_path_with_email(self):
        response = self.client.post(reverse('login'), {
            "username_or_email": "old@example.com",
            "password": "12345"
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_login_sad_path_wrong_credentials(self):
        response = self.client.post(reverse('login'), {
            "username_or_email": "old",
            "password": "wrong"
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse('_auth_user_id' in self.client.session)

    # ---------------------------
    # REGISTER
    # ---------------------------
    def test_register_happy_path(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'phone': '0911111111',
            'password': 'abc123',
            'confirm_password': 'abc123',
            'first_name': 'New',
            'last_name': 'User',
            'country': 'TH',
            'city': 'Bangkok'
        })
        self.assertEqual(User.objects.filter(username="newuser").count(), 1)
        self.assertEqual(Profile.objects.filter(user__username="newuser").count(), 1)
        self.assertRedirects(response, reverse('login'))

    def test_register_sad_path_password_mismatch(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'phone': '0911111111',
            'password': 'abc123',
            'confirm_password': '4321cba',
            'first_name': 'New',
            'last_name': 'User',
            'country': 'TH',
            'city': 'Bangkok'
        })
        self.assertEqual(User.objects.filter(username="newuser").count(), 0)

    def test_register_sad_path_duplicate_username(self):
        response = self.client.post(reverse('register'), {
            'username': 'old',
            'email': 'new@example.com',
            'phone': '0911111111',
            'password': 'abc123',
            'confirm_password': 'abc123',
            'first_name': 'New',
            'last_name': 'User',
            'country': 'TH',
            'city': 'Bangkok'
        })
        self.assertEqual(User.objects.filter(email="new@example.com").count(), 0)

    def test_register_sad_path_duplicate_email(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'old@example.com',
            'phone': '0911111111',
            'password': 'abc123',
            'confirm_password': 'abc123',
            'first_name': 'New',
            'last_name': 'User',
            'country': 'TH',
            'city': 'Bangkok'
        })
        self.assertEqual(User.objects.filter(username="newuser").count(), 0)

    def test_register_sad_path_wrong_phone_pattern(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'phone': '1234',
            'password': 'abc123',
            'confirm_password': 'abc123',
            'first_name': 'New',
            'last_name': 'User',
            'country': 'TH',
            'city': 'Bangkok'
        })
        self.assertEqual(User.objects.filter(username="newuser").count(), 0)

    # ---------------------------
    # PROFILE
    # ---------------------------
    def test_profile_happy_path_user_logged_in(self):
        self.client.login(username="old", password="12345")
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bangkok")

    def test_profile_sad_path_user_not_logged_in(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    # ---------------------------
    # LOGOUT
    # ---------------------------
    def test_logout_happy_path(self):
        self.client.login(username="old", password="12345")
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertFalse('_auth_user_id' in self.client.session)

    ## other test
    def test_register_page_get(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

class NotificationViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.url = reverse('notifications') 

        # สร้างข้อมูลจำลอง (Mock Data)
        self.notification_unread = Notification.objects.create(
            user=self.user,
            is_read=False,
            # เพิ่ม fields อื่นๆ ที่ model Notification จำเป็นต้องมี (ถ้ามี)
        )
        self.notification_read = Notification.objects.create(
            user=self.user,
            is_read=True
        )

    def test_notification_list_access_authenticated(self):
        """ทดสอบว่า user ที่ login แล้วสามารถเข้าถึงหน้านี้ได้"""
        self.client.login(username='testuser', password='password')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/notification.html")
        self.assertIn("notifications", response.context)
        # ตรวจสอบว่า query มาครบทั้ง 2 อัน
        self.assertEqual(len(response.context["notifications"]), 2)

    def test_notification_list_marks_as_read(self):
        """ทดสอบว่าเมื่อเข้าหน้านี้ notification ที่ is_read=False ถูกเปลี่ยนเป็น True"""
        self.client.login(username='testuser', password='password')
        self.client.get(self.url)
        
        self.notification_unread.refresh_from_db()
        self.assertTrue(self.notification_unread.is_read)

    def test_notification_list_access_unauthenticated(self):
        """ทดสอบว่าถ้ายังไม่ login จะถูก redirect (302)"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

MEDIA_ROOT = tempfile.mkdtemp()

@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ProfileEditViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        # สร้าง User หลัก
        self.user = User.objects.create_user(username='testuser', email='test@test.com', password='password')
        
        if not hasattr(self.user, 'profile'):
            Profile.objects.create(user=self.user)
            
        self.url = reverse('profile_edit')
        self.success_url = reverse('profile')

    def tearDown(self):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def test_profile_edit_access_get(self):
        """ทดสอบการเข้าหน้าแก้ไขโปรไฟล์ (GET)"""
        self.client.login(username='testuser', password='password')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile_edit_page.html')
        self.assertIsInstance(response.context['u_form'], UserUpdateForm)
        self.assertIsInstance(response.context['p_form'], ProfileUpdateForm)

    def test_profile_update_success(self):
        """ทดสอบการอัพเดทข้อมูลสำเร็จ"""
        self.client.login(username='testuser', password='password')
        
        data = {
            'username': 'newusername',
            'email': 'new@test.com',
            # ใส่ข้อมูล required ของ Profile ถ้ามี (ในที่นี้ image blank=True)
        }
        
        response = self.client.post(self.url, data)
        
        # ตรวจสอบว่า redirect ไปหน้า profile
        self.assertRedirects(response, self.success_url)
        
        # ตรวจสอบข้อมูลใน DB
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'newusername')
        self.assertEqual(self.user.email, 'new@test.com')

    def test_profile_update_username_taken(self):
        """ทดสอบกรณีเปลี่ยน username เป็นชื่อที่มีอยู่แล้ว"""
        User.objects.create_user(username='otheruser', password='password')
        self.client.login(username='testuser', password='password')
        
        data = {
            'username': 'otheruser', 
            'email': 'test@test.com',
        }
        
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        
        form_errors = response.context['u_form'].errors
        self.assertIn('username', form_errors)
        # เช็คว่ามี error กลับมา (ไม่ต้องระบุข้อความเป๊ะๆ ก็ได้ เพื่อความยืดหยุ่น)
        self.assertTrue(len(form_errors['username']) > 0)

    def test_remove_image(self):
        """ทดสอบปุ่มลบรูปภาพ"""
        self.client.login(username='testuser', password='password')
        
        # จำลองการมีรูปภาพอยู่ก่อน
        image = SimpleUploadedFile("test_image.jpg", b"file_content", content_type="image/jpeg")
        self.user.profile.image = image
        self.user.profile.save()
        
        # ส่ง POST request พร้อมปุ่ม remove_image
        data = {
            'remove_image': 'true', # ค่า value ไม่สำคัญ ขอแค่มี key
             # ต้องส่งข้อมูล form หลักไปด้วยเพราะ view อาจจะ validate ก่อน (ขึ้นอยู่กับ logic flow)
             # แต่ในโค้ดของคุณเช็ค `if 'remove_image'` ก่อน `form.is_valid` เลยไม่ต้องส่ง field อื่นก็ได้
        }
        
        response = self.client.post(self.url, data)
        
        # ตรวจสอบ redirect กลับมาหน้า edit (ตามโค้ดของคุณ)
        self.assertRedirects(response, self.url)
        
        # ตรวจสอบว่ารูปกลายเป็น default
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.image.name, 'default.jpg')

    def test_login_required(self):
        """ทดสอบว่าต้อง login ก่อนเข้าใช้งาน"""
        response = self.client.get(self.url)
        self.assertRedirects(response, f'/accounts/login/?next={self.url}')

class UserProfilePageViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        # สร้าง User เป้าหมาย
        self.target_user = User.objects.create_user(username='targetuser', password='password')
        
        # สร้าง User อื่น (เพื่อเช็คว่าจะไม่เห็นโพสต์ของคนนี้)
        self.other_user = User.objects.create_user(username='otheruser', password='password')

        # สร้าง Posts ของ target_user
        self.post1 = Post.objects.create(
            author=self.target_user,
            title="Target Post 1",
            content="Content 1",
            animal_type="dog",
            animal_race="golden_retriever"
        )
        self.post2 = Post.objects.create(
            author=self.target_user,
            title="Target Post 2",
            content="Content 2",
            animal_type="cat"
        )

        # สร้าง Post ของ user อื่น
        self.other_post = Post.objects.create(
            author=self.other_user,
            title="Other Post",
            content="Content Other"
        )

        # URL Name (สมมติว่าเป็น 'user_profile')
        self.url = reverse('user_profile', args=[self.target_user.username])

    def test_user_profile_page_success(self):
        """ทดสอบการเข้าถึงหน้าโปรไฟล์ของ User ที่มีอยู่จริง"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/user_profile_page.html')
        
        # ตรวจสอบ Context
        self.assertEqual(response.context['profile_user'], self.target_user)
        
        # ตรวจสอบว่ามี Post ของ target_user ครบ
        posts_in_context = response.context['posts']
        self.assertEqual(posts_in_context.count(), 2)
        self.assertIn(self.post1, posts_in_context)
        self.assertIn(self.post2, posts_in_context)
        
        # ตรวจสอบว่า **ไม่มี** Post ของคนอื่นปนมา
        self.assertNotIn(self.other_post, posts_in_context)

    def test_user_profile_page_not_found(self):
        """ทดสอบการเข้าถึงหน้าโปรไฟล์ของ User ที่ไม่มีอยู่จริง (ต้องได้ 404)"""
        url_404 = reverse('user_profile', args=['nonexistent_user'])
        response = self.client.get(url_404)
        
        self.assertEqual(response.status_code, 404)

class MyBookmarksViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.other_user = User.objects.create_user(username='otheruser', password='password')
        
        self.url = reverse('my_bookmarks') 

        self.post1 = Post.objects.create(
            author=self.other_user, 
            title="Post 1 (Old)", 
            content="Content 1"
        )
        self.post2 = Post.objects.create(
            author=self.other_user, 
            title="Post 2 (New)", 
            content="Content 2"
        )
        self.post3_not_bookmarked = Post.objects.create(
            author=self.other_user, 
            title="Post 3", 
            content="Content 3"
        )

        self.post1.bookmarks.add(self.user)
        self.post2.bookmarks.add(self.user)
        
    def test_my_bookmarks_access_authenticated(self):
        self.client.login(username='testuser', password='password')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/my_bookmarks_page.html")
        
        posts = response.context['posts']
        self.assertEqual(posts.count(), 2)
        
        self.assertIn(self.post1, posts)
        self.assertIn(self.post2, posts)
        
        self.assertNotIn(self.post3_not_bookmarked, posts)

    def test_my_bookmarks_ordering(self):
        self.client.login(username='testuser', password='password')
        response = self.client.get(self.url)
        
        posts = list(response.context['posts'])
        self.assertEqual(posts[0], self.post2)
        self.assertEqual(posts[1], self.post1)

    def test_login_required(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

class DeleteNotificationViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.other_user = User.objects.create_user(username='otheruser', password='password')
        
        self.post = Post.objects.create(
            author=self.other_user, 
            title="Test Post", 
            content="Content"
        )

        self.notification = Notification.objects.create(
            user=self.user,
            actor=self.other_user,
            notification_type='like',
            message='liked your post',
            post=self.post
        )
        
        self.notification_other = Notification.objects.create(
            user=self.other_user,
            actor=self.user,
            notification_type='comment',
            message='commented',
            post=self.post
        )

        self.url = reverse('delete_notification', args=[self.notification.pk])
        self.success_url = reverse('notifications')

    def test_delete_notification_success(self):
        self.client.login(username='testuser', password='password')
        response = self.client.get(self.url)
        
        self.assertRedirects(response, self.success_url)
        self.assertFalse(Notification.objects.filter(pk=self.notification.pk).exists())

    def test_delete_other_user_notification(self):
        self.client.login(username='testuser', password='password')
        url = reverse('delete_notification', args=[self.notification_other.pk]) 
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Notification.objects.filter(pk=self.notification_other.pk).exists())