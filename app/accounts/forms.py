from django import forms
from django.contrib.auth.models import User
from .models import Profile

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full rounded-md border-gray-300 dark:border-gray-600 focus:ring-accent focus:border-accent',
                'placeholder': 'Enter your username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full rounded-md border-gray-300 dark:border-gray-600 focus:ring-accent focus:border-accent',
                'placeholder': 'Enter your email'
            }),
        }


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Styling the file input
        file_input_classes = (
            "w-full text-sm text-text dark:text-darktext "
            "border border-border dark:border-darkborder rounded-lg "
            "cursor-pointer bg-background dark:bg-darkbg focus:outline-none"
        )
        self.fields['image'].widget.attrs.update({'class': file_input_classes})
