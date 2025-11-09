from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from app.shelters.models import ShelterProfile
from app.posts.models import Post

class ShelterViewsTest(TestCase):

    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            password='password123'
        )
        self.client.login(username='testuser', password='password123')

    def test_shelter_register_view_creates_profile(self):
        """User without shelter should be able to register a shelter."""
        response = self.client.post(reverse('shelter_register'), {
            'name': 'Happy Pets Shelter',
            'address': '123 Road',
            'phone': '0999999999',
            'description': 'We take care of cute animals.'
        })

        # Check shelter created
        self.assertTrue(ShelterProfile.objects.filter(user=self.user).exists())
        self.assertRedirects(response, reverse('shelter_profile'))

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

        post1 = Post.objects.create(title="Pet A", shelter=shelter)
        post2 = Post.objects.create(title="Pet B", shelter=shelter)

        response = self.client.get(reverse('shelter_profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Shelter')
        self.assertIn('shelter_posts', response.context)
        self.assertEqual(list(response.context['shelter_posts']), [post2, post1])  # ordered desc

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
