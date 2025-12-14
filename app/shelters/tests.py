from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from app.shelters.models import ShelterProfile
from app.posts.models import Post
from django.core.files.uploadedfile import SimpleUploadedFile

class ShelterViewsTest(TestCase):

    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            password='password123'
        )
        self.client.login(username='testuser', password='password123')
    
    def test_shelter_register_redirect_if_profile_exists(self):
        """User with existing shelter should be redirected."""
        ShelterProfile.objects.create(
            user=self.user,
            name='Already Exists',
            address='Somewhere',
            phone='0123456789'
        )

        response = self.client.get(reverse('shelter_register'))
        self.assertRedirects(response, reverse('shelter_profile'))

    def test_shelter_profile_view_displays_correct_data(self):
        """Shelter data and posts should appear in profile page."""
        shelter = ShelterProfile.objects.create(
            user=self.user,
            name='Test Shelter',
            address='Test Address',
            phone='0123456789'
        )

        post1 = Post.objects.create(title="Pet A", shelter=shelter, author=self.user)
        post2 = Post.objects.create(title="Pet B", shelter=shelter, author=self.user)

        response = self.client.get(reverse('shelter_profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Shelter')
        self.assertIn('shelter_posts', response.context)
        self.assertCountEqual(response.context['shelter_posts'], [post1, post2])


    def test_shelter_update_view(self):
        """User should be able to update their shelter."""
        shelter = ShelterProfile.objects.create(
            user=self.user,
            name='Old Name',
            address='Old Address',
            phone='0123456789'
        )

        response = self.client.post(reverse('shelter_update'), {
            'name': 'New Name',
            'address': 'New Address',
            'phone': '0888888888',
            'description': 'Updated shelter info'
        })

        shelter.refresh_from_db()
        self.assertEqual(shelter.name, 'New Name')
        self.assertRedirects(response, reverse('shelter_profile'))

class ShelterRegisterViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('shelter_register') # เปลี่ยนเป็นชื่อ URL ของ View นี้
        self.redirect_url = reverse('shelter_profile') # เปลี่ยนเป็นชื่อ URL ปลายทางที่ redirect ไป
        
        # User 1: ยังไม่มี Shelter Profile
        self.user_no_profile = User.objects.create_user(username='new', password='password')
        
        # User 2: มี Shelter Profile แล้ว
        self.user_with_profile = User.objects.create_user(username='existing', password='password')
        ShelterProfile.objects.create(
            user=self.user_with_profile,
            name="Existing Shelter",
            description="Desc",
            address="Addr",
            phone="123",
            email="test@shelter.com",
            verification_document=SimpleUploadedFile("doc.pdf", b"content"),
            status='APPROVED'
        )

    def test_dispatch_redirects_if_profile_exists(self):
        self.client.login(username='existing', password='password')
        response = self.client.get(self.url)
        
        # ต้อง Redirect ไปหน้า shelter_profile เพราะมีโปรไฟล์แล้ว
        self.assertRedirects(response, self.redirect_url)

    def test_form_valid_assigns_user(self):
        self.client.login(username='new', password='password')
        
        # ส่ง Data เพื่อเข้า form_valid
        file_data = SimpleUploadedFile("doc.pdf", b"file_content")
        data = {
            'name': 'New Shelter',
            'description': 'Description',
            'address': 'Address',
            'phone': '0812345678',
            'email': 'new@shelter.com',
            'verification_document': file_data
        }
        
        response = self.client.post(self.url, data)
        
        # เช็คว่าสร้างสำเร็จ (Redirect ไป success url ของ view นั้น - อาจจะเป็น shelter_profile หรือหน้าอื่น)
        self.assertEqual(response.status_code, 302) 
        
        # เช็คว่ามีการสร้าง Profile และผูกกับ User ถูกต้อง
        self.assertTrue(ShelterProfile.objects.filter(user=self.user_no_profile).exists())

class PublicShelterProfileViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='test', password='password')
        self.shelter = ShelterProfile.objects.create(
            user=self.user,
            name="Shelter",
            status='APPROVED'
        )
        Post.objects.create(author=self.user, shelter=self.shelter, title="Post", content="Content")
        
        self.url = reverse('public_shelter_profile', args=[self.shelter.pk]) # เช็คชื่อ URL ใน urls.py

    def test_view_coverage(self):
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shelters/public_shelter_profile.html')
        self.assertIn('shelter_posts', response.context)