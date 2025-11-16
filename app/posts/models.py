from django.db import models
from django.contrib.auth.models import User
from app.shelters.models import ShelterProfile

class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    shelter = models.ForeignKey(ShelterProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='posts')
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='post_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
