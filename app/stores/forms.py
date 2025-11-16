from django import forms
from .models import Store, Product

class StoreRequestForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ['name', 'description', 'store_type', 'profile_image', 'cover_image', 'verification_document', 'verification_statement']

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
        fields = ['name', 'description', 'profile_image', 'cover_image']

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