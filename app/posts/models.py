from django.db import models
from django.contrib.auth.models import User
from app.shelters.models import ShelterProfile


# ================================
# TAG MODEL
# ================================
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# ================================
# POST MODEL
# ================================
TAG_CHOICES = [
    ('none', 'ไม่มีแท็ก'),
    ('missing', 'สัตว์หาย'),
    ('adoption_update', 'อัปเดตการรับเลี้ยง'),
    ('qa', 'Q&A'),
    ('other', 'อื่นๆ'),
    ('care', 'เคล็ดลับการดูแลสัตว์'),
    ('health', 'สุขภาพ/หมอ'),
    ('success', 'เรื่องราวความสำเร็จ'),
    ('event', 'กิจกรรมรับเลี้ยง'),
    ('found', 'พบสัตว์หลง'),
]

class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    shelter = models.ForeignKey(ShelterProfile, on_delete=models.CASCADE,
                                null=True, blank=True, related_name='posts')

    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='post_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    #  TAG FIELD (fixed choices)
    tag = models.CharField(max_length=50, choices=TAG_CHOICES, default='none')

    # Location
    location = models.CharField(max_length=255, blank=True, null=True)

    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    bookmarks = models.ManyToManyField(User, related_name='bookmarked_posts', blank=True)

    def __str__(self):
        return self.title


# ================================
# COMMENT MODEL
# ================================
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author.username} on {self.post.title}'