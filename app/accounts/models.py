from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    score = models.IntegerField(default=100, verbose_name="User Score")
    image = models.ImageField(
        default='default.jpg',
        upload_to='profile_pics',
        verbose_name="Profile Image"
    )

    def __str__(self):
        return self.user.username


class Notification(models.Model):
    """
    Stores all updates for a user:
    - like
    - comment
    - system message, etc.
    """

    NOTIFICATION_TYPES = [
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('system', 'System'),
    ]

    # คนที่ได้รับการแจ้งเตือน
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    # คนที่ทำ action (เช่น คนที่มากดไลค์ / คอมเมนต์)
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications'
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='system'
    )

    # ข้อความที่จะแสดงใน noti เช่น "Ploy liked your post"
    message = models.CharField(max_length=255)

    # ถ้าจะผูกกับโพสต์ (optional)
    post = models.ForeignKey(
        'posts.Post',                 # string app.Model ช่วยเลี่ยง import วนกัน
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )

    #  สถานะอ่าน / ยังไม่อ่าน
    is_read = models.BooleanField(default=False)

    # เวลาเกิด noti
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']   # อันใหม่อยู่บนสุด

    def __str__(self):
        return f"{self.user.username} - {self.notification_type} - {self.message}"
