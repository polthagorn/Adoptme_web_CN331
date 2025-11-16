from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name="dashboard_home"),
    path("shelters/", views.shelter_approval, name="shelter_approval"),
    path("shelters/<int:shelter_id>/approve/", views.approve_shelter, name="approve_shelter"),
    path("shelters/<int:shelter_id>/reject/", views.reject_shelter, name="reject_shelter"),
    path("users/", views.user_list, name="dashboard_users"),
    path("users/delete/<int:user_id>/", views.delete_user, name="delete_user"),
    path("stores/", views.store_approval, name="store_approval"),
    path("stores/<int:store_id>/approve/", views.approve_store, name="approve_store"),
    path("stores/<int:store_id>/reject/", views.reject_store, name="reject_store"),


]
