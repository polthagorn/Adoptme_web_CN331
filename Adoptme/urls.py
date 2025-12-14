from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from app.posts import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.welcome, name='welcome'),
    path('home/', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('posts/', include('app.posts.urls')),
    path('accounts/', include('app.accounts.urls')),
    path('stores/', include('app.stores.urls')),
    path('shelters/', include('app.shelters.urls')),
    path('dashboard/', include('app.dashboard.urls')),
    path('chat/', include('app.chats.urls')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
