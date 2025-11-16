from django import forms
from django.contrib.auth.models import User
from .models import Profile

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        # only allow updating username for simplicity
        fields = ['username']

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        # only allow updating image for simplicity
        fields = ['image']

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
        

            file_input_classes = "w-full text-sm text-text dark:text-darktext border border-border dark:border-darkborder rounded-lg cursor-pointer bg-background dark:bg-darkbg focus:outline-none"
            self.fields['image'].widget.attrs.update({'class': file_input_classes})