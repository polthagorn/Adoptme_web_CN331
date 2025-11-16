from django.urls import path
from .views import ShelterRegisterView, ShelterProfileView, ShelterUpdateView, PublicShelterProfileView

urlpatterns = [
    path('register/', ShelterRegisterView.as_view(), name='shelter_register'),
    path('profile/', ShelterProfileView.as_view(), name='shelter_profile'),
    path('edit/', ShelterUpdateView.as_view(), name='shelter_update'),
    path('view/<int:pk>/', PublicShelterProfileView.as_view(), name='public_shelter_profile'),
]
