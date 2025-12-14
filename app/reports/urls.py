from django.urls import path
from . import views

urlpatterns = [
    path("new/", views.create_report, name="create_report"),

    # user report search page
    path("users/", views.report_user_search, name="report_user_search"),

    # staff views
    path("bug/", views.report_bug, name="report_bug"),
    path("admin/", views.admin_report_list, name="admin_report_list"),
    path("admin/<int:pk>/", views.admin_report_detail, name="admin_report_detail"),
]
