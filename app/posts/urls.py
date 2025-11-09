from django.urls import path
from . import views

urlpatterns = [
    path('home/', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('posts/', views.post, name='posts'),
    path('new/', views.create_post, name='create_post'),
    path('<int:post_id>/', views.post_detail, name='post_detail'),
    path('<int:post_id>/edit/', views.edit_post, name='edit_post'),
    path('<int:post_id>/delete/', views.delete_post, name='delete_post'),
]
