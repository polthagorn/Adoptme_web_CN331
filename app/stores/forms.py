from django import forms
from .models import Store, Product, StoreReview, ProductReview, Store, Payment, Order

class StoreRequestForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ['name', 'description', 'store_type', 'profile_image', 'cover_image', 'verification_document', 'verification_statement', 'payment_qr', 'bank_details']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common_classes = "w-full p-2 border border-border dark:border-darkborder rounded-md bg-background dark:bg-darkbg text-text dark:text-darktext focus:ring-accent focus:border-accent"
        image_classes = "w-full text-sm text-text dark:text-darktext border border-border dark:border-darkborder rounded-lg cursor-pointer bg-background dark:bg-darkbg"

        self.fields['name'].widget.attrs.update({'class': common_classes})
        self.fields['description'].widget.attrs.update({'class': common_classes, 'rows': 4})
        self.fields['store_type'].widget.attrs.update({'class': common_classes})
        self.fields['profile_image'].widget.attrs.update({'class': image_classes})
        self.fields['cover_image'].widget.attrs.update({'class': image_classes})
        self.fields['verification_document'].widget.attrs.update({'class': image_classes})
        self.fields['verification_statement'].widget.attrs.update({'class': common_classes, 'rows': 4})

    def clean(self):
        cleaned_data = super().clean()
        document = cleaned_data.get('verification_document')
        statement = cleaned_data.get('verification_statement')

        if not document and not statement:
            raise forms.ValidationError(
                "Please provide either a verification document or a statement. You must submit at least one."
            )
        return cleaned_data

class StoreUpdateForm(forms.ModelForm):
    class Meta:
        model = Store
        # only allow updating name, description, profile_image, and cover_image
        fields = ['name', 'description', 'profile_image', 'cover_image', 'payment_qr', 'bank_details']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # tailwindcss classes
        common_classes = "w-full p-2 border border-border dark:border-darkborder rounded-md bg-background dark:bg-darkbg text-text dark:text-darktext focus:ring-accent focus:border-accent"
        image_classes = "w-full text-sm text-text dark:text-darktext border border-border dark:border-darkborder rounded-lg cursor-pointer bg-background dark:bg-darkbg"

        self.fields['name'].widget.attrs.update({'class': common_classes})
        self.fields['description'].widget.attrs.update({'class': common_classes, 'rows': 4})
        self.fields['profile_image'].widget.attrs.update({'class': 'w-full text-sm text-text dark:text-darktext border border-border dark:border-darkborder rounded-lg cursor-pointer bg-background dark:bg-darkbg'})
        self.fields['profile_image'].widget.attrs.update({'class': image_classes})
        self.fields['cover_image'].widget.attrs.update({'class': image_classes})

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'image', 'stock']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common_classes = "w-full p-2 border border-border dark:border-darkborder rounded-md bg-background dark:bg-darkbg text-text dark:text-darktext focus:ring-accent focus:border-accent"
        self.fields['name'].widget.attrs.update({'class': common_classes})
        self.fields['description'].widget.attrs.update({'class': common_classes, 'rows': 4})
        self.fields['price'].widget.attrs.update({'class': common_classes, 'type': 'number', 'step': '0.01'})
        self.fields['image'].widget.attrs.update({'class': 'w-full text-sm text-text dark:text-darktext border border-border dark:border-darkborder rounded-lg cursor-pointer bg-background dark:bg-darkbg'})
        self.fields['stock'].widget.attrs.update({'class': common_classes, 'type': 'number'})

class StoreReviewForm(forms.ModelForm):
    class Meta:
        model = StoreReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'w-full p-2 ...'}), # ใส่คลาส Tailwind
            'comment': forms.Textarea(attrs={'rows': 4, 'class': 'w-full p-2 ...'}), # ใส่คลาส Tailwind
        }

class ProductReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'w-full p-2 ...'}), # ใส่คลาส Tailwind
            'comment': forms.Textarea(attrs={'rows': 4, 'class': 'w-full p-2 ...'}), # ใส่คลาส Tailwind
        }

class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1, 
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'w-20 p-2 border border-border dark:border-darkborder rounded-md bg-background dark:bg-darkbg text-text dark:text-darktext text-center',
            'placeholder': '1'
        })
    )

class PaymentForm(forms.ModelForm):
    amount = forms.DecimalField(required=True, widget=forms.NumberInput(attrs={'class': 'w-full p-2 border border-border dark:border-darkborder rounded-md bg-background dark:bg-darkbg text-text dark:text-darktext'}))
    transfer_date = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-2 border border-border dark:border-darkborder rounded-md bg-background dark:bg-darkbg text-text dark:text-darktext'}))
    transfer_time = forms.TimeField(required=True, widget=forms.TimeInput(attrs={'type': 'time', 'class': 'w-full p-2 border border-border dark:border-darkborder rounded-md bg-background dark:bg-darkbg text-text dark:text-darktext'}))
    slip_image = forms.ImageField(required=True, widget=forms.FileInput(attrs={'class': 'w-full text-sm text-text dark:text-darktext border border-border dark:border-darkborder rounded-lg cursor-pointer bg-background dark:bg-darkbg focus:outline-none'}))

    class Meta:
        model = Payment
        fields = ['amount', 'transfer_date', 'transfer_time', 'slip_image']

class OrderStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'w-full p-2 border rounded bg-white dark:bg-darkbg text-text dark:text-darktext'})
        }

class OrderShippingForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status', 'tracking_number', 'shipping_proof']
        widgets = {
            'status': forms.Select(attrs={'class': 'w-full p-2 border rounded bg-background dark:bg-darkbg text-text dark:text-darktext'}),
            'tracking_number': forms.TextInput(attrs={'class': 'w-full p-2 border rounded bg-background dark:bg-darkbg text-text dark:text-darktext'}),
            'shipping_proof': forms.FileInput(attrs={'class': 'w-full p-2 border rounded bg-background dark:bg-darkbg text-text dark:text-darktext'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if self.instance.pk:
            current_status = self.instance.status
            allowed_choices = []

            # 1. รอจ่าย: ยกเลิกได้ (เพราะยังไม่ได้เงิน)
            if current_status == 'PENDING':
                allowed_choices = [
                    ('PENDING', 'Waiting for Payment'),
                    ('CANCELLED', 'Cancel Order') # ยังยกเลิกได้
                ]
            
            # 2. จ่ายแล้ว: ห้ามยกเลิก (ต้องกด Confirm เท่านั้น)
            elif current_status == 'PAID':
                allowed_choices = [
                    ('PAID', 'Payment Submitted'),
                    ('CONFIRMED', 'Confirm Order')
                ]
            
            # 3. ยืนยันแล้ว: ห้ามยกเลิก (ต้องกด Ship เท่านั้น)
            elif current_status == 'CONFIRMED':
                allowed_choices = [
                    ('CONFIRMED', 'Order Confirmed'),
                    ('SHIPPED', 'Ship Order') 
                ]
            
            # 4. ส่งแล้ว: รอจบงาน
            elif current_status == 'SHIPPED':
                allowed_choices = [
                    ('SHIPPED', 'Shipped'), 
                ]
            
            # 5. จบ/ยกเลิก: แก้ไขไม่ได้แล้ว
            else:
                allowed_choices = [(current_status, self.instance.get_status_display())]
                self.fields['status'].disabled = True

            self.fields['status'].choices = allowed_choices

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        tracking = cleaned_data.get('tracking_number')
        proof = cleaned_data.get('shipping_proof')

        if status == 'SHIPPED':
            if not tracking:
                self.add_error('tracking_number', 'Tracking number is required for shipped status.')
            if not proof and not self.instance.shipping_proof:
                self.add_error('shipping_proof', 'Shipping proof image is required.')
        
        return cleaned_data