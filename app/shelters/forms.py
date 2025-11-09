from django import forms
from .models import ShelterProfile

class ShelterRegistrationForm(forms.ModelForm):
    class Meta:
        model = ShelterProfile
        fields = [
            'name', 'description', 'address', 'phone_number',
            'profile_image', 'cover_image', 'verification_document'
        ]
        help_texts = {
            'verification_document': 'Please upload verification documents (.pdf, .jpg, .png)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common_classes = "w-full p-2 border border-border dark:border-darkborder rounded-md bg-background dark:bg-darkbg text-text dark:text-darktext focus:ring-accent focus:border-accent"
        
        # กำหนดคลาส CSS สำหรับช่องอัปโหลดไฟล์
        file_input_classes = "w-full text-sm text-text dark:text-darktext border border-border dark:border-darkborder rounded-lg cursor-pointer bg-background dark:bg-darkbg focus:outline-none"

        # นำคลาสไปใช้กับแต่ละฟิลด์
        self.fields['name'].widget.attrs.update({'class': common_classes})
        self.fields['description'].widget.attrs.update({'class': common_classes, 'rows': 4})
        self.fields['address'].widget.attrs.update({'class': common_classes, 'rows': 3})
        self.fields['phone_number'].widget.attrs.update({'class': common_classes})
        
        self.fields['profile_image'].widget.attrs.update({'class': file_input_classes})
        self.fields['cover_image'].widget.attrs.update({'class': file_input_classes})
        self.fields['verification_document'].widget.attrs.update({'class': file_input_classes})