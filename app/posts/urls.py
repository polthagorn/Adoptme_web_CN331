from django.urls import path
from . import views

urlpatterns = [
    # POST LIST / FEED
    path('', views.post, name='posts'),

    # CREATE NEW POST
    path('new/', views.create_post, name='create_post'),

    # POST DETAIL ( + COMMENT SUBMIT inside this view )
    path('<int:post_id>/', views.post_detail, name='post_detail'),

    # EDIT POST
    path('<int:post_id>/edit/', views.edit_post, name='edit_post'),

    # DELETE POST
    path('<int:post_id>/delete/', views.delete_post, name='delete_post'),

    # LIKE POST ( ⚡ notification fires here )
    path('<int:post_id>/like/', views.like_post, name='like_post'),

    # BOOKMARK POST
    path('<int:post_id>/bookmark/', views.bookmark_post, name='bookmark_post'),
]
