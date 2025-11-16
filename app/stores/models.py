# app/stores/models.py
from django.db import models
from django.contrib.auth.models import User

class Store(models.Model):
    # --- ย้ายโค้ดทั้งหมดนี้เข้ามาในคลาส Store ---
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

    # --- เพิ่มฟิลด์สำหรับ Verification ---
    verification_document = models.FileField(upload_to='store_verification_docs/', null=True, blank=True, verbose_name="Verification Document")
    verification_statement = models.TextField(null=True, blank=True, verbose_name="Verification Statement")

    # --- เพิ่มฟิลด์สำหรับ Verification ---
    verification_document = models.FileField(upload_to='store_verification_docs/', null=True, blank=True, verbose_name="Verification Document")
    verification_statement = models.TextField(null=True, blank=True, verbose_name="Verification Statement")

    def __str__(self): # pragma: no cover
        return self.name

class Product(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255, verbose_name="product name")
    description = models.TextField(verbose_name="product description")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="product price")
    image = models.ImageField(upload_to='product_images/', blank=True, null=True, verbose_name="product image")
    stock = models.PositiveIntegerField(default=0, verbose_name="stock quantity")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): # pragma: no cover
        return self.name
    
class StoreReview(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='reviews')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)]) # 1-5 ดาว
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        # บังคับให้ 1 user รีวิว 1 ร้านค้าได้แค่ครั้งเดียว
        unique_together = ('store', 'author')

    def __str__(self):
        return f'{self.rating} stars for {self.store.name} by {self.author.username}'

class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)]) # 1-5 ดาว
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        # บังคับให้ 1 user รีวิว 1 สินค้าได้แค่ครั้งเดียว
        unique_together = ('product', 'author')

    def __str__(self):
        return f'{self.rating} stars for {self.product.name} by {self.author.username}'