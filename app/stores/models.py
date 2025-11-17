from django.db import models
from django.contrib.auth.models import User

class Store(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'pending'),
        ('APPROVED', 'approved'),
        ('REJECTED', 'rejected'),
    ]
    STORE_TYPE_CHOICES = [
        ('PET', 'pet shop'),
        ('SUPPLIES', 'supplies shop'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stores')
    name = models.CharField(max_length=255, verbose_name="store name")
    description = models.TextField(verbose_name="store description")
    store_type = models.CharField(max_length=10, choices=STORE_TYPE_CHOICES, verbose_name="store type")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING', verbose_name="store status")
    created_at = models.DateTimeField(auto_now_add=True)

    profile_image = models.ImageField(upload_to='store_profiles/', null=True, blank=True, verbose_name="profile image")
    cover_image = models.ImageField(upload_to='store_covers/', null=True, blank=True, verbose_name="cover image")

    def __str__(self):
        return self.name

class Product(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255, verbose_name="product name")
    description = models.TextField(verbose_name="product description")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="product price")
    image = models.ImageField(upload_to='product_images/', blank=True, null=True, verbose_name="product image")
    stock = models.PositiveIntegerField(default=0, verbose_name="stock quantity")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name