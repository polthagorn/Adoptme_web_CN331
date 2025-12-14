from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from app.posts.models import Post, Comment
from app.posts.forms import PostForm
from app.shelters.models import ShelterProfile
from app.accounts.models import Notification

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

    def test_welcome_page(self):
        response = self.client.get(reverse('welcome'))
        self.assertEqual(response.status_code, 200)

    def test_home_page(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_about_page(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)

class DeletePostViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='owner', password='password')
        self.other_user = User.objects.create_user(username='other', password='password')
        
        self.post = Post.objects.create(
            author=self.user,
            title="Post to Delete",
            content="Content"
        )
        
        self.url = reverse('delete_post', args=[self.post.id]) 
        self.success_url = reverse('posts') 

    def test_get_request_renders_confirmation(self):
        self.client.login(username='owner', password='password')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'posts/delete_post.html')

    def test_post_request_deletes_object(self):
        self.client.login(username='owner', password='password')
        response = self.client.post(self.url)
        
        self.assertRedirects(response, self.success_url)
        self.assertFalse(Post.objects.filter(id=self.post.id).exists())

    def test_delete_other_user_post_404(self):
        self.client.login(username='other', password='password')
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Post.objects.filter(id=self.post.id).exists())

class EditPostViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        
        self.post = Post.objects.create(
            author=self.user,
            title="Old Title",
            content="Old Content",
            tag="missing",
            animal_type="dog"
        )
        
        self.url = reverse('edit_post', args=[self.post.id]) # เช็คชื่อ URL ใน urls.py
        self.success_url = reverse('posts') # เช็คชื่อ URL ใน urls.py

    def test_edit_post_get_coverage(self):
        self.client.login(username='testuser', password='password')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'posts/edit_post.html')

    def test_edit_post_post_coverage(self):
        self.client.login(username='testuser', password='password')
        
        data = {
            'title': 'New Title',
            'content': 'New Content',
            'tag': 'found',
            'animal_type': 'cat',
            'animal_race': 'persian'
        }
        
        response = self.client.post(self.url, data)
        
        self.assertRedirects(response, self.success_url)
        
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, 'New Title')

class PostTagFilterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        
        self.post_lost = Post.objects.create(
            author=self.user, 
            title="Lost Dog", 
            content="...", 
            tag="lost"
        )
        
        self.post_found = Post.objects.create(
            author=self.user, 
            title="Found Cat", 
            content="...", 
            tag="found"
        )
        
        self.url = reverse('posts')

    def test_filter_by_specific_tag(self):
        response = self.client.get(self.url, {'tag': 'lost'})
        
        self.assertEqual(response.status_code, 200)
        posts = response.context['posts']
        
        self.assertIn(self.post_lost, posts)
        self.assertNotIn(self.post_found, posts)

    def test_filter_tag_none_returns_all(self):
        response = self.client.get(self.url, {'tag': 'none'})
        
        self.assertEqual(response.status_code, 200)
        posts = response.context['posts']
        
        self.assertIn(self.post_lost, posts)
        self.assertIn(self.post_found, posts)

    def test_no_tag_param_returns_all(self):
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        posts = response.context['posts']
        
        self.assertIn(self.post_lost, posts)
        self.assertIn(self.post_found, posts)

class PostFilterCoverageTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='test', password='password')
        
        self.post = Post.objects.create(
            author=self.user,
            title="Test Post",
            content="Content",
            tag="lost",
            animal_type="Dog"
        )
        
        self.url = reverse('posts')

    def test_filters_coverage(self):
        response = self.client.get(self.url, {
            'tag': 'lost',
            'animal_type': 'Dog'
        })
        
        self.assertEqual(response.status_code, 200)

class PostRaceFilterCoverageTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='test', password='password')
        
        self.post = Post.objects.create(
            author=self.user,
            title="Test Post",
            content="Content",
            animal_race="Golden"
        )
        
        self.url = reverse('posts')

    def test_animal_race_filter_coverage(self):
        response = self.client.get(self.url, {
            'animal_race': 'Golden'
        })
        
        self.assertEqual(response.status_code, 200)

class PostLocationLogicTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='test', password='password')
        Post.objects.create(author=self.user, title="Post", content="Content")
        
        self.url = reverse('posts') 

    def test_location_valid_params(self):
        response = self.client.get(self.url, {
            'center_lat': '13.75',
            'center_lng': '100.50',
            'radius_km': '10'
        })
        self.assertEqual(response.status_code, 200)

    def test_location_invalid_params(self):
        response = self.client.get(self.url, {
            'center_lat': 'invalid_lat',
            'center_lng': '100.50',
            'radius_km': '10'
        })
        self.assertEqual(response.status_code, 200)

class PostHaversineFilterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='test', password='password')
        
        self.post_near = Post.objects.create(
            author=self.user,
            title="Near",
            content="Content",
            latitude=13.7563,
            longitude=100.5018
        )

        self.post_far = Post.objects.create(
            author=self.user,
            title="Far",
            content="Content",
            latitude=14.0000,
            longitude=100.5018
        )

        self.post_no_loc = Post.objects.create(
            author=self.user,
            title="No Loc",
            content="Content",
            latitude=None,
            longitude=None
        )
        
        self.url = reverse('posts') 

    def test_haversine_calculation_and_sorting(self):
        response = self.client.get(self.url, {
            'center_lat': '13.7563',
            'center_lng': '100.5018',
            'radius_km': '10'
        })
        
        self.assertEqual(response.status_code, 200)

class CreatePostViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        self.user = User.objects.create_user(username='user', password='password')
        
        self.shelter_owner = User.objects.create_user(username='owner', password='password')
        
        dummy_file = SimpleUploadedFile("doc.pdf", b"file_content")
        self.shelter = ShelterProfile.objects.create(
            user=self.shelter_owner,
            name="Test Shelter",
            description="Desc",
            address="Addr",
            phone="123",
            email="test@shelter.com",
            verification_document=dummy_file,
            status='APPROVED'
        )
        
        self.url = reverse('create_post')
        self.success_url = reverse('posts')

    def test_get_create_post_page(self):
        self.client.login(username='user', password='password')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_create_post_regular_user(self):
        self.client.login(username='user', password='password')
        
        data = {
            'title': 'Lost Dog',
            'content': 'Please help find my dog',
            'tag': 'missing',
            'animal_type': 'dog',
            'animal_race': 'golden_retriever',
            'location': 'Bangkok'
        }
        
        response = self.client.post(self.url, data)
        
        self.assertRedirects(response, self.success_url)
        
        post = Post.objects.last()
        self.assertEqual(post.title, 'Lost Dog')
        self.assertEqual(post.author, self.user)
        self.assertIsNone(post.shelter)

    def test_create_post_shelter_user_auto_assign(self):
        self.client.login(username='owner', password='password')
        
        data = {
            'title': 'Shelter Update',
            'content': 'We have new pets',
            'tag': 'adoption_update',
            'animal_type': 'cat',
            'animal_race': 'persian'
        }
        
        response = self.client.post(self.url, data)
        
        self.assertRedirects(response, self.success_url)
        
        post = Post.objects.last()
        self.assertEqual(post.author, self.shelter_owner)
        self.assertEqual(post.shelter, self.shelter)

    def test_create_post_invalid_form(self):
        self.client.login(username='user', password='password')
        
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].is_valid())
        self.assertTrue(response.context['form'].errors)

class PostDetailNotificationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.author = User.objects.create_user(username='author', password='password')
        self.commenter = User.objects.create_user(username='commenter', password='password')
        
        self.post = Post.objects.create(
            author=self.author,
            title="Test Post",
            content="Content"
        )
        
        self.url = reverse('post_detail', args=[self.post.id])

    def test_get_request_renders_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_comment_by_other_user_creates_notification(self):
        self.client.login(username='commenter', password='password')
        
        data = {'content': 'Great post!'}
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, 302) 
        
        self.assertEqual(Comment.objects.count(), 1)
        
        self.assertEqual(Notification.objects.count(), 1)
        noti = Notification.objects.first()
        self.assertEqual(noti.user, self.author) 
        self.assertEqual(noti.actor, self.commenter) 
        self.assertEqual(noti.notification_type, 'comment')

    def test_comment_by_author_does_not_create_notification(self):
        self.client.login(username='author', password='password')
        
        data = {'content': 'My reply'}
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, 302)
        
        self.assertEqual(Comment.objects.count(), 1)
        
        self.assertEqual(Notification.objects.count(), 0)

    def test_unauthenticated_comment_redirects(self):
        data = {'content': 'Spam'}
        response = self.client.post(self.url, data)
        
        self.assertNotEqual(response.status_code, 200)
        self.assertTrue(response.status_code in [302, 301])

class LikePostViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.author = User.objects.create_user(username='author', password='password')
        self.user = User.objects.create_user(username='user', password='password')
        
        self.post = Post.objects.create(
            author=self.author,
            title="Test Post",
            content="Content"
        )
        
        self.url = reverse('like_post', args=[self.post.id]) 
        self.fallback_url = reverse('posts') 

    def test_like_post_creates_like_and_notification(self):
        self.client.login(username='user', password='password')
        
        # จำลอง HTTP_REFERER
        header = {'HTTP_REFERER': '/previous/url/'}
        response = self.client.get(self.url, **header)
        
        self.assertRedirects(response, '/previous/url/', fetch_redirect_response=False)
        
        # Check Like added
        self.assertTrue(self.post.likes.filter(id=self.user.id).exists())
        
        # Check Notification created
        self.assertEqual(Notification.objects.count(), 1)
        noti = Notification.objects.first()
        self.assertEqual(noti.user, self.author)
        self.assertEqual(noti.actor, self.user)
        self.assertEqual(noti.notification_type, 'like')

    def test_unlike_post_removes_like(self):
        self.client.login(username='user', password='password')
        
        # ให้ User like ไปก่อน
        self.post.likes.add(self.user)
        
        response = self.client.get(self.url)
        
        # Check Redirect to fallback (ไม่มี referer)
        self.assertRedirects(response, self.fallback_url)
        
        # Check Like removed
        self.assertFalse(self.post.likes.filter(id=self.user.id).exists())

    def test_like_own_post_no_notification(self):
        self.client.login(username='author', password='password')
        
        response = self.client.get(self.url)
        
        # Check Like added
        self.assertTrue(self.post.likes.filter(id=self.author.id).exists())
        
        # Check Notification NOT created
        self.assertEqual(Notification.objects.count(), 0)

    def test_like_nonexistent_post_404(self):
        self.client.login(username='user', password='password')
        url = reverse('like_post', args=[999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

class BookmarkPostViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.post = Post.objects.create(
            author=self.user,
            title="Test Post",
            content="Content"
        )
        
        self.url = reverse('bookmark_post', args=[self.post.id])
        self.fallback_url = reverse('posts')

    def test_bookmark_add(self):
        self.client.login(username='testuser', password='password')
        
        # จำลอง HTTP_REFERER
        header = {'HTTP_REFERER': '/previous/page/'}
        response = self.client.get(self.url, **header)
        
        self.assertRedirects(response, '/previous/page/', fetch_redirect_response=False)
        self.assertTrue(self.post.bookmarks.filter(id=self.user.id).exists())

    def test_bookmark_remove(self):
        self.client.login(username='testuser', password='password')
        
        # เพิ่ม bookmark ไว้ก่อน
        self.post.bookmarks.add(self.user)
        
        response = self.client.get(self.url)
        
        self.assertRedirects(response, self.fallback_url)
        self.assertFalse(self.post.bookmarks.filter(id=self.user.id).exists())

    def test_bookmark_invalid_post_404(self):
        self.client.login(username='testuser', password='password')
        url = reverse('bookmark_post', args=[999])
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)