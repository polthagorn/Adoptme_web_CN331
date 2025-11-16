from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    score = models.IntegerField(default=100, verbose_name="User Score")
    image = models.ImageField(default='default.jpg', upload_to='profile_pics', verbose_name="Profile Image")

    def __str__(self):
        return self.user.username