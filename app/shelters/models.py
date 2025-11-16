from django.db import models
from django.contrib.auth.models import User

class ShelterProfile(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'pending'),
        ('APPROVED', 'approved'),
        ('REJECTED', 'rejected'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='shelter_profile')

    name = models.CharField(max_length=255, verbose_name="shelter name")
    description = models.TextField(verbose_name="about the shelter")
    address = models.TextField(verbose_name="address")
    phone = models.CharField(max_length=20, verbose_name="phone number")
    email = models.EmailField(verbose_name="email address")

    profile_image = models.ImageField(upload_to='shelter_profiles/', null=True, blank=True, verbose_name="profile image")
    cover_image = models.ImageField(upload_to='shelter_covers/', null=True, blank=True, verbose_name="cover image")
    
    verification_document = models.FileField(upload_to='shelter_verification_docs/', verbose_name="verification document")
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING', verbose_name="status")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): # pragma: no cover
        return self.name