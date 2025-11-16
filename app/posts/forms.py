from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'image', 'location', 'tag']
        widgets = {
            'tag': forms.Select(attrs={
                'class': 'w-full p-2 border border-border dark:border-darkborder rounded-md bg-background dark:bg-darkbg text-text dark:text-darktext'
            }),
            'location': forms.TextInput(attrs={
                'class': 'w-full p-2 border border-border dark:border-darkborder rounded-md bg-background dark:bg-darkbg text-text dark:text-darktext',
                'placeholder': 'สถานที่ (เช่น Bangkok)'
            }),
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
