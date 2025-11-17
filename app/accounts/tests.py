from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from app.accounts.models import Profile


class AuthViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="john",
            email="john@example.com",
            password="12345"
        )
        Profile.objects.create(user=self.user, phone="111", country="TH", city="Bangkok")

    # ---------------------------
    # LOGIN
    # ---------------------------
    def test_login_happy_path_with_username(self):
        response = self.client.post(reverse('login'), {
            "username_or_email": "john",
            "password": "12345"
        })
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_login_happy_path_with_email(self):
        response = self.client.post(reverse('login'), {
            "username_or_email": "john@example.com",
            "password": "12345"
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_login_sad_path_wrong_credentials(self):
        response = self.client.post(reverse('login'), {
            "username_or_email": "john",
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
            'phone': '222',
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
            'password': 'abc123',
            'confirm_password': 'xyz789'
        })
        self.assertEqual(User.objects.filter(username="newuser").count(), 0)

    def test_register_sad_path_duplicate_username(self):
        response = self.client.post(reverse('register'), {
            'username': 'john',  # already exists
            'email': 'another@example.com',
            'password': '123',
            'confirm_password': '123'
        })
        self.assertEqual(User.objects.filter(email="another@example.com").count(), 0)

    def test_register_sad_path_duplicate_email(self):
        response = self.client.post(reverse('register'), {
            'username': 'anotheruser',
            'email': 'john@example.com',  # existing email
            'password': '123',
            'confirm_password': '123'
        })
        self.assertEqual(User.objects.filter(username="anotheruser").count(), 0)

    # ---------------------------
    # PROFILE
    # ---------------------------
    def test_profile_happy_path_user_logged_in(self):
        self.client.login(username="john", password="12345")
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
        self.client.login(username="john", password="12345")
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertFalse('_auth_user_id' in self.client.session)
