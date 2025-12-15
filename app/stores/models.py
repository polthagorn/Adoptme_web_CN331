# app/stores/models.py
from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from app.accounts.models import Notification

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

    # เพิ่ม QR Code สำหรับรับเงิน
    payment_qr = models.ImageField(upload_to='store_qrs/', null=True, blank=True, verbose_name="Payment QR Code")
    bank_details = models.TextField(null=True, blank=True, verbose_name="Bank Account Details (Optional)")

    followers = models.ManyToManyField(User, related_name='following_stores', blank=True)

    def __str__(self): # pragma: no cover
        return self.name
    
    # Helper Function: ตรวจสอบว่าสินค้ากำลังลดราคาอยู่หรือไม่
    @property
    def is_on_sale(self):
        return self.discount_price is not None and self.discount_price > 0 and self.discount_price < self.price

    # Helper Function: ดึงราคาขายจริง (ถ้าลดก็เอาราคาลด ถ้าไม่ลดก็ราคาเต็ม)
    @property
    def sell_price(self):
        if self.is_on_sale:
            return self.discount_price
        return self.price

class Product(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255, verbose_name="product name")
    description = models.TextField(verbose_name="product description")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="product price")
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Discount Price")
    image = models.ImageField(upload_to='product_images/', blank=True, null=True, verbose_name="product image")
    stock = models.PositiveIntegerField(default=0, verbose_name="stock quantity")
    created_at = models.DateTimeField(auto_now_add=True)
    discount_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Discount Price (Optional)"
    )

    # Helper: เช็คว่าสินค้านี้ลดราคาอยู่ไหม
    @property
    def is_on_sale(self):
        return self.discount_price is not None and 0 < self.discount_price < self.price

    # Helper: คืนค่าราคาขายจริง (ถ้าลดก็เอาราคาลด ถ้าไม่ลดก็ราคาเต็ม)
    @property
    def sell_price(self):
        if self.is_on_sale:
            return self.discount_price
        return self.price

    # Helper: คำนวณ % ส่วนลด (เอาไว้โชว์ป้าย -20%)
    @property
    def discount_percent(self):
        if self.is_on_sale:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return 0

    def __str__(self): # pragma: no cover
        return self.name
    
class StoreReview(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='reviews')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)]) # 1-5 ดาว
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='store_reviews/', blank=True, null=True, verbose_name="Review Image")

    class Meta:
        ordering = ['-created_at']
        # บังคับให้ 1 user รีวิว 1 ร้านค้าได้แค่ครั้งเดียว
        unique_together = ('store', 'author')

    def __str__(self):
        return f'{self.rating} stars for {self.store.name} by {self.author.username}'

class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='product_reviews')
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)]) # 1-5 ดาว
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='product_reviews/', blank=True, null=True, verbose_name="Review Image")

    class Meta:
        ordering = ['-created_at']
        # บังคับให้ 1 user รีวิว 1 สินค้าได้แค่ครั้งเดียว
        unique_together = ('product', 'author', 'order')

    def __str__(self):
        return f'{self.rating} stars for {self.product.name} by {self.author.username}'
    
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    def __str__(self):
        return f"Cart of {self.user.username}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    is_selected = models.BooleanField(default=True) 

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def total_price(self):
        return self.product.sell_price * self.quantity

# -- เพิ่มโค้ดสำหรับการสั่งซื้อสินค้า (Orders) ---

# สร้าง Model สำหรับใบสั่งซื้อ (Order)
class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Waiting for Payment'),   # 1. สั่งซื้อยังไม่จ่าย
        ('PAID', 'Payment Submitted'),        # 2. จ่ายแล้ว (รอร้านตรวจสอบ)
        ('CONFIRMED', 'Payment Confirmed'),   # 2.5 ร้านยืนยันการจ่ายเงินแล้ว
        ('SHIPPED', 'Shipped'),               # 3. จัดส่งแล้ว
        ('COMPLETED', 'Received'),            # 4. รับของแล้ว
        ('CANCELLED', 'Cancelled'),           # 5. ยกเลิกแล้ว
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    tracking_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tracking Number")
    shipping_proof = models.ImageField(upload_to='shipping_proofs/', blank=True, null=True, verbose_name="Shipping Proof")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.store.name}"

# สร้าง Model สำหรับรายการสินค้าในออเดอร์ (Snapshot ราคาตอนซื้อ)
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2) # ราคาต่อชิ้นตอนที่กดซื้อ
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    @property
    def total_price(self):
        return self.price * self.quantity
        

# สร้าง Model สำหรับแจ้งชำระเงิน (Payment)
class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Amount Transferred")
    transfer_date = models.DateField(verbose_name="Transfer Date")
    transfer_time = models.TimeField(verbose_name="Transfer Time")
    slip_image = models.ImageField(upload_to='payment_slips/', null=True, blank=True, verbose_name="Transfer Slip") # ควรมีรูปสลิปด้วยเพื่อความชัวร์
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for Order #{self.order.id}"
    
@receiver(pre_save, sender=Store)
def store_status_notification(sender, instance, **kwargs):
    if instance.pk: # ตรวจสอบว่าเป็นร้านที่มีอยู่แล้ว (ไม่ใช่การสร้างใหม่)
        try:
            old_store = Store.objects.get(pk=instance.pk)
            
            # เช็คว่าสถานะเปลี่ยนจาก PENDING เป็นอย่างอื่นหรือไม่
            if old_store.status == 'PENDING' and instance.status != 'PENDING':
                
                message = ""
                if instance.status == 'APPROVED':
                    message = f"🎉 Your store <b>{instance.name}</b> has been <b>APPROVED</b>! You can now start selling."
                elif instance.status == 'REJECTED':
                    message = f"❌ Your store <b>{instance.name}</b> has been <b>REJECTED</b>. Please contact admin for details."
                
                if message:
                    Notification.objects.create(
                        user=instance.owner,  # ส่งให้เจ้าของร้าน
                        actor=None,           # เป็น System Notification (ไม่มีคนกระทำ)
                        notification_type='system',
                        message=message
                    )
                    
        except Store.DoesNotExist:
            pass