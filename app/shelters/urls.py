from django.urls import path
from .views import ShelterRegisterView, ShelterProfileView, ShelterUpdateView

urlpatterns = [
    path('register/', ShelterRegisterView.as_view(), name='shelter_register'),
    path('profile/', ShelterProfileView.as_view(), name='shelter_profile'),
    path('edit/', ShelterUpdateView.as_view(), name='shelter_update'),
]