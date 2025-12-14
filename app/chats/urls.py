from django.urls import path
from . import views

urlpatterns = [
    path("", views.inbox, name="chat_inbox"),
    path("dm/<int:user_id>/", views.start_dm, name="chat_start_dm"),
    path("<int:pk>/", views.thread, name="chat_thread"),
    path("unread/", views.unread_counts, name="chat_unread_counts"),    
]
