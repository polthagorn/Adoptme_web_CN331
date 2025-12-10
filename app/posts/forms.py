from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = [
            'title',
            'content',
            'image',
            'tag',          # หมวดหมู่โพสต์
            'animal_type',  # 🐾 ประเภทสัตว์ (ใหม่)
            'animal_race',  # 🐾 สายพันธุ์/สายเลือด (ใหม่)
            'location',
            'latitude',
            'longitude',
        ]

        widgets = {
            'tag': forms.Select(attrs={
                'class': 'w-full p-2 border border-border dark:border-darkborder rounded-md bg-background dark:bg-darkbg text-text dark:text-darktext'
            }),

            # 🐾 ประเภทสัตว์ (dropdown)
            'animal_type': forms.Select(attrs={
                'class': 'w-full p-2 border border-border dark:border-darkborder rounded-md bg-background dark:bg-darkbg text-text dark:text-darktext'
            }),

            # 🐾 สายพันธุ์ / สายเลือด (dropdown)
            'animal_race': forms.Select(attrs={
                'class': 'w-full p-2 border border-border dark:border-darkborder rounded-md bg-background dark:bg-darkbg text-text dark:text-darktext'
            }),

            # location text (optional: district, province, etc.)
            'location': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-border dark:border-darkborder rounded-md bg-background dark:bg-darkbg text-text dark:text-darktext',
                'placeholder': 'สถานที่ (เช่น Bangkok หรือ หมู่บ้าน...)'
            }),

            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'w-full p-2 border border-border dark:border-darkborder rounded-md bg-background dark:bg-darkbg text-text dark:text-darktext focus:ring-accent focus:border-accent',
                'rows': 3,
                'placeholder': 'Add a comment...'
            })
        }
        labels = {
            'content': ''
        }
