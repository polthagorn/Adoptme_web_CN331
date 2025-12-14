from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_home, name="dashboard_home"),

    path("shelters/", views.shelter_approval, name="shelter_approval"),
    path("shelters/<int:shelter_id>/approve/", views.approve_shelter, name="approve_shelter"),
    path("shelters/<int:shelter_id>/reject/", views.reject_shelter, name="reject_shelter"),

    path("stores/", views.store_approval, name="store_approval"),
    path("stores/<int:store_id>/approve/", views.approve_store, name="approve_store"),
    path("stores/<int:store_id>/reject/", views.reject_store, name="reject_store"),

    path("users/", views.user_list, name="dashboard_users"),
    path("users/<int:user_id>/delete/", views.delete_user, name="dashboard_delete_user"),
    path("users/<int:user_id>/score/", views.update_user_score, name="dashboard_update_user_score"),
    path("users/<int:user_id>/ban/", views.ban_user, name="dashboard_ban_user"),
    path("users/<int:user_id>/unban/", views.unban_user, name="dashboard_unban_user"),
]