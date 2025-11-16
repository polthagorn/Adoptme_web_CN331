from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_page, name='login'),
    path('register/', views.register_page, name='register'),
    path('logout/', views.logout_page, name='logout'),
    path('profile/', views.profile_page, name='profile'),
    path('profile/edit/', views.profile_edit_page, name='profile_edit'),
    path('user/<str:username>/', views.user_profile_page, name='user_profile'),
]