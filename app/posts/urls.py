from django.urls import path
from . import views

urlpatterns = [
    path('about/', views.about, name='about'),
    path('posts/', views.post, name='posts'),
]
