from django import forms
from .models import Store, Product

class StoreRequestForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ['name', 'description', 'store_type', 'profile_image', 'cover_image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common_classes = "w-full p-2 border border-border dark:border-darkborder rounded-md bg-background dark:bg-darkbg text-text dark:text-darktext focus:ring-accent focus:border-accent"
        image_classes = "w-full text-sm text-text dark:text-darktext border border-border dark:border-darkborder rounded-lg cursor-pointer bg-background dark:bg-darkbg"

        self.fields['name'].widget.attrs.update({'class': common_classes})
        self.fields['description'].widget.attrs.update({'class': common_classes, 'rows': 4})
        self.fields['store_type'].widget.attrs.update({'class': common_classes})
        self.fields['profile_image'].widget.attrs.update({'class': image_classes})
        self.fields['cover_image'].widget.attrs.update({'class': image_classes})

class StoreUpdateForm(forms.ModelForm):
    class Meta:
        model = Store
        # อนุญาตให้แก้ไขได้แค่ชื่อ, คำอธิบาย, รูปโปรไฟล์, และรูปหน้าปก
        fields = ['name', 'description', 'profile_image', 'cover_image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # กำหนดคลาส Tailwind ให้กับฟอร์ม
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