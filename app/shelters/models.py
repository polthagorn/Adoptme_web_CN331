from django.db import models
from django.contrib.auth.models import User

class ShelterProfile(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='shelter_profile'
    )

    name = models.CharField(
        max_length=255,
        verbose_name="Shelter name"
    )
    description = models.TextField(
        verbose_name="About the shelter"
    )
    address = models.TextField(
        verbose_name="Address"
    )
    phone = models.CharField(
        max_length=20,
        verbose_name="Phone number"
    )
    email = models.EmailField(
        verbose_name="Email address"
    )

    profile_image = models.ImageField(
        upload_to='shelter_profiles/',
        null=True,
        blank=True,
        verbose_name="Profile image"
    )
    cover_image = models.ImageField(
        upload_to='shelter_covers/',
        null=True,
        blank=True,
        verbose_name="Cover image"
    )

    verification_document = models.FileField(
        upload_to='shelter_verification_docs/',
        verbose_name="Verification document"
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="Status"
    )

    # field นี้
    rejection_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name="Rejection reason"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    followers = models.ManyToManyField(
        User, 
        related_name='following_shelters', 
        blank=True
    )


    def __str__(self):  # pragma: no cover
        return self.name
