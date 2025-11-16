from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from app.posts.models import Post
from app.posts.forms import PostForm

class PostViewsTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Users
        self.user = User.objects.create_user(username="john", password="12345")
        self.other = User.objects.create_user(username="kate", password="12345")

        # Post owned by self.user
        self.post = Post.objects.create(
            title="My First Post",
            content="Hello!",
            author=self.user
        )

    # -------------------------
    # List posts
    # -------------------------
    def test_post_list_displays_posts(self):
        response = self.client.get(reverse('posts'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My First Post")

    # -------------------------
    # Create Post
    # -------------------------
    def test_create_post_get(self):
        self.client.login(username='john', password='12345')
        response = self.client.get(reverse('create_post'))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], PostForm)

    def test_create_post_happy_path(self):
        self.client.login(username="john", password="12345")
        response = self.client.post(reverse('create_post'), {
            'title': 'New Post',
            'content': 'This is new!'
        })
        self.assertTrue(Post.objects.filter(title='New Post').exists())
        self.assertRedirects(response, reverse('posts'))

    def test_create_post_sad_path_not_logged_in(self):
        response = self.client.get(reverse('create_post'))
        self.assertEqual(response.status_code, 302)  # redirect to login page

    # -------------------------
    # Edit Post
    # -------------------------
    def test_edit_post_get(self):
        self.client.login(username='john', password='12345')
        response = self.client.get(reverse('edit_post', args=[self.post.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'posts/edit_post.html')
        self.assertEqual(response.context['form'].instance, self.post)
    
    def test_edit_post_happy_path(self):
        self.client.login(username="john", password="12345")
        response = self.client.post(reverse('edit_post', args=[self.post.id]), {
            'title': 'Updated Title',
            'content': 'Updated content'
        })
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, 'Updated Title')
        self.assertRedirects(response, reverse('posts'))

    def test_edit_post_sad_path_other_user_cannot_edit(self):
        self.client.login(username="kate", password="12345")
        response = self.client.get(reverse('edit_post', args=[self.post.id]))
        self.assertEqual(response.status_code, 404)  # blocked by author check

    # -------------------------
    # Post Detail
    # -------------------------
    def test_post_detail_displays_correct_post(self):
        response = self.client.get(reverse('post_detail', args=[self.post.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My First Post")

    def test_post_detail_sad_path_post_not_found(self):
        response = self.client.get(reverse('post_detail', args=[999]))
        self.assertEqual(response.status_code, 404)

    # -------------------------
    # Delete Post
    # -------------------------
    def test_delete_post_happy_path(self):
        self.client.login(username="john", password="12345")
        response = self.client.post(reverse('delete_post', args=[self.post.id]))
        self.assertEqual(Post.objects.count(), 0)
        self.assertRedirects(response, reverse('posts'))

    def test_delete_post_sad_path_other_user_cannot_delete(self):
        self.client.login(username="kate", password="12345")
        response = self.client.post(reverse('delete_post', args=[self.post.id]))
        self.assertEqual(response.status_code, 404)  # blocked by author filter

    def test_welcome_page(self):
        response = self.client.get(reverse('welcome'))
        self.assertEqual(response.status_code, 200)

    def test_home_page(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_about_page(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)
