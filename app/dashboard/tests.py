from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages import get_messages
from app.shelters.models import ShelterProfile
from app.stores.models import Store

class DashboardHomeStatsTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        self.superuser = User.objects.create_superuser(
            username='admin', email='admin@test.com', password='password'
        )
        
        User.objects.create_user(username='user1', password='password')
        
        self.owner_pending = User.objects.create_user(username='owner1', password='password')
        self.owner_approved = User.objects.create_user(username='owner2', password='password')

        dummy_file = SimpleUploadedFile("doc.pdf", b"file_content")

        ShelterProfile.objects.create(
            user=self.owner_pending,
            name="Pending Shelter",
            description="Desc",
            address="Addr",
            phone="123",
            email="p@s.com",
            verification_document=dummy_file,
            status='PENDING'
        )

        ShelterProfile.objects.create(
            user=self.owner_approved,
            name="Approved Shelter",
            description="Desc",
            address="Addr",
            phone="123",
            email="a@s.com",
            verification_document=dummy_file,
            status='APPROVED'
        )
        
        self.url = reverse('dashboard_home')

    def test_dashboard_stats_context(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/index.html")
        
        self.assertEqual(response.context['total_users'], 4)
        
        self.assertEqual(response.context['total_shelters'], 2)
        
        self.assertEqual(response.context['pending_shelter_approvals'], 1)

class ShelterApprovalTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        self.superuser = User.objects.create_superuser(
            username='admin', email='admin@test.com', password='password'
        )
        
        self.regular_user = User.objects.create_user(
            username='user', email='user@test.com', password='password'
        )
        
        self.shelter_owner_1 = User.objects.create_user(username='owner1', password='password')
        self.shelter_owner_2 = User.objects.create_user(username='owner2', password='password')

        dummy_file = SimpleUploadedFile("doc.pdf", b"file_content")

        self.shelter_pending = ShelterProfile.objects.create(
            user=self.shelter_owner_1,
            name="Pending Shelter",
            description="Test Desc",
            address="Test Addr",
            phone="0812345678",
            email="test@shelter.com",
            verification_document=dummy_file,
            status='PENDING'
        )

        self.shelter_approved = ShelterProfile.objects.create(
            user=self.shelter_owner_2,
            name="Approved Shelter",
            description="Test Desc",
            address="Test Addr",
            phone="0812345678",
            email="test2@shelter.com",
            verification_document=dummy_file,
            status='APPROVED'
        )

        self.list_url = reverse('shelter_approval') 

    def test_superuser_can_see_pending_shelters(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/shelter_approval.html")
        
        shelters = response.context['shelters']
        self.assertIn(self.shelter_pending, shelters)
        self.assertNotIn(self.shelter_approved, shelters)

    def test_regular_user_cannot_access_dashboard(self):
        self.client.login(username='user', password='password')
        response = self.client.get(self.list_url)
        
        self.assertNotEqual(response.status_code, 200)

    def test_superuser_approve_shelter_action(self):
        self.client.login(username='admin', password='password')
        approve_url = reverse('approve_shelter', args=[self.shelter_pending.id]) # เช็คชื่อ URL ใน urls.py
        
        response = self.client.get(approve_url)
        
        self.assertRedirects(response, self.list_url)
        
        self.shelter_pending.refresh_from_db()
        self.assertEqual(self.shelter_pending.status, 'APPROVED')

    def test_regular_user_cannot_approve_shelter(self):
        self.client.login(username='user', password='password')
        approve_url = reverse('approve_shelter', args=[self.shelter_pending.id]) # เช็คชื่อ URL ใน urls.py
        
        response = self.client.get(approve_url)
        
        if response.status_code == 302:
             self.assertNotEqual(response.url, self.list_url)
        else:
             self.assertNotEqual(response.status_code, 200)

        self.shelter_pending.refresh_from_db()
        self.assertEqual(self.shelter_pending.status, 'PENDING')

class RejectShelterViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        self.superuser = User.objects.create_superuser(
            username='admin', email='admin@test.com', password='password'
        )
        
        self.regular_user = User.objects.create_user(
            username='user', email='user@test.com', password='password'
        )

        self.owner = User.objects.create_user(username='owner', password='password')
        
        dummy_file = SimpleUploadedFile("doc.pdf", b"file_content")

        self.shelter = ShelterProfile.objects.create(
            user=self.owner,
            name="Test Shelter",
            description="Desc",
            address="Addr",
            phone="123",
            email="s@s.com",
            verification_document=dummy_file,
            status="PENDING"
        )

        self.url = reverse('reject_shelter', args=[self.shelter.id])
        self.success_url = reverse('shelter_approval')

    def test_superuser_reject_shelter_post_success(self):
        self.client.login(username='admin', password='password')
        
        data = {'reason': 'Invalid documentation'}
        response = self.client.post(self.url, data)
        
        self.assertRedirects(response, self.success_url)
        
        self.shelter.refresh_from_db()
        self.assertEqual(self.shelter.status, 'REJECTED')
        self.assertEqual(self.shelter.rejection_reason, 'Invalid documentation')
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(len(messages) > 0)
        self.assertIn("Shelter 'Test Shelter' has been rejected.", str(messages[0]))

    def test_superuser_reject_shelter_get_request_no_change(self):
        self.client.login(username='admin', password='password')
        
        response = self.client.get(self.url)
        
        self.assertRedirects(response, self.success_url)
        
        self.shelter.refresh_from_db()
        self.assertEqual(self.shelter.status, 'PENDING')

    def test_regular_user_cannot_reject(self):
        self.client.login(username='user', password='password')
        
        data = {'reason': 'Malicious attempt'}
        response = self.client.post(self.url, data)
        
        if response.status_code == 302:
             self.assertNotEqual(response.url, self.success_url)
        else:
             self.assertNotEqual(response.status_code, 200)

        self.shelter.refresh_from_db()
        self.assertEqual(self.shelter.status, 'PENDING')

class UserListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        self.superuser = User.objects.create_superuser(
            username='admin', email='admin@test.com', password='password'
        )
        
        self.user1 = User.objects.create_user(username='user1', password='password')
        self.user2 = User.objects.create_user(username='user2', password='password')
        
        self.url = reverse('dashboard_users')

    def test_superuser_can_see_user_list(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/user_list.html")
        
        users_in_context = response.context['users']
        self.assertEqual(users_in_context.count(), 3)
        
        self.assertEqual(users_in_context[0], self.user2)
        self.assertEqual(users_in_context[1], self.user1)

    def test_regular_user_cannot_access(self):
        self.client.login(username='user1', password='password')
        response = self.client.get(self.url)
        
        self.assertNotEqual(response.status_code, 200)

class DeleteUserViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        self.admin = User.objects.create_superuser(
            username='admin', email='admin@test.com', password='password'
        )
        
        self.other_admin = User.objects.create_superuser(
            username='other_admin', email='other@test.com', password='password'
        )
        
        self.regular_user = User.objects.create_user(
            username='user', email='user@test.com', password='password'
        )
        
        self.success_url = reverse('dashboard_users')

    def test_admin_delete_regular_user_success(self):
        self.client.login(username='admin', password='password')
        url = reverse('delete_user', args=[self.regular_user.id])
        
        response = self.client.get(url)
        
        self.assertRedirects(response, self.success_url)
        
        self.assertFalse(User.objects.filter(id=self.regular_user.id).exists())
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "User deleted successfully.")

    def test_admin_cannot_delete_self(self):
        self.client.login(username='admin', password='password')
        url = reverse('delete_user', args=[self.admin.id])
        
        response = self.client.get(url)
        
        self.assertRedirects(response, self.success_url)
        
        self.assertTrue(User.objects.filter(id=self.admin.id).exists())
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "You cannot delete your own account.")

    def test_admin_cannot_delete_other_admin(self):
        self.client.login(username='admin', password='password')
        url = reverse('delete_user', args=[self.other_admin.id])
        
        response = self.client.get(url)
        
        self.assertRedirects(response, self.success_url)
        
        self.assertTrue(User.objects.filter(id=self.other_admin.id).exists())
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "You cannot delete another admin.")

    def test_regular_user_cannot_delete(self):
        self.client.login(username='user', password='password')
        url = reverse('delete_user', args=[self.admin.id])
        
        response = self.client.get(url)
        
        self.assertNotEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(id=self.admin.id).exists())

class StoreApprovalViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        self.superuser = User.objects.create_superuser(
            username='admin', email='admin@test.com', password='password'
        )
        
        self.regular_user = User.objects.create_user(
            username='user', email='user@test.com', password='password'
        )
        
        self.owner = User.objects.create_user(username='owner', password='password')

        dummy_file = SimpleUploadedFile("doc.pdf", b"file_content")

        self.store_pending = Store.objects.create(
            owner=self.owner,
            name="Pending Store",
            description="Desc",
            store_type="PET",
            status="PENDING",
            verification_document=dummy_file
        )

        self.store_approved = Store.objects.create(
            owner=self.owner,
            name="Approved Store",
            description="Desc",
            store_type="SUPPLIES",
            status="APPROVED",
            verification_document=dummy_file
        )

        self.url = reverse('store_approval')

    def test_superuser_can_see_pending_stores(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/store_approval.html")
        
        stores = response.context['stores']
        self.assertIn(self.store_pending, stores)
        self.assertNotIn(self.store_approved, stores)

    def test_regular_user_cannot_access(self):
        self.client.login(username='user', password='password')
        response = self.client.get(self.url)
        
        self.assertNotEqual(response.status_code, 200)

class ApproveStoreViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        self.superuser = User.objects.create_superuser(
            username='admin', email='admin@test.com', password='password'
        )
        
        self.regular_user = User.objects.create_user(
            username='user', email='user@test.com', password='password'
        )
        
        self.owner = User.objects.create_user(username='owner', password='password')
        
        dummy_file = SimpleUploadedFile("doc.pdf", b"file_content")

        self.store = Store.objects.create(
            owner=self.owner,
            name="Pending Store",
            description="Desc",
            store_type="PET",
            status="PENDING",
            verification_document=dummy_file
        )

        self.url = reverse('approve_store', args=[self.store.id])
        self.success_url = reverse('store_approval')

    def test_superuser_approve_store_success(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(self.url)
        
        self.assertRedirects(response, self.success_url)
        
        self.store.refresh_from_db()
        self.assertEqual(self.store.status, 'APPROVED')
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "Store 'Pending Store' approved.")

    def test_regular_user_cannot_approve(self):
        self.client.login(username='user', password='password')
        response = self.client.get(self.url)
        
        if response.status_code == 302:
             self.assertNotEqual(response.url, self.success_url)
        else:
             self.assertNotEqual(response.status_code, 200)

        self.store.refresh_from_db()
        self.assertEqual(self.store.status, 'PENDING')

class RejectStoreViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        self.superuser = User.objects.create_superuser(
            username='admin', email='admin@test.com', password='password'
        )
        
        self.regular_user = User.objects.create_user(
            username='user', email='user@test.com', password='password'
        )
        
        self.owner = User.objects.create_user(username='owner', password='password')
        
        dummy_file = SimpleUploadedFile("doc.pdf", b"file_content")

        self.store = Store.objects.create(
            owner=self.owner,
            name="Pending Store",
            description="Desc",
            store_type="PET",
            status="PENDING",
            verification_document=dummy_file
        )

        self.url = reverse('reject_store', args=[self.store.id])
        self.success_url = reverse('store_approval')

    def test_superuser_reject_store_success(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(self.url)
        
        self.assertRedirects(response, self.success_url)
        
        self.store.refresh_from_db()
        self.assertEqual(self.store.status, 'REJECTED')
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "Store 'Pending Store' rejected.")

    def test_regular_user_cannot_reject(self):
        self.client.login(username='user', password='password')
        response = self.client.get(self.url)
        
        if response.status_code == 302:
             self.assertNotEqual(response.url, self.success_url)
        else:
             self.assertNotEqual(response.status_code, 200)

        self.store.refresh_from_db()
        self.assertEqual(self.store.status, 'PENDING')