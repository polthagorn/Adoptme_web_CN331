from django.urls import path
from .views import (
    StoreRequestCreateView, 
    MyStoreListView, 
    ProductCreateView,
    MarketplaceView,
    ProductDetailView,
    StoreManageView,
    StoreProfileView,
    StoreUpdateView,
    ProductUpdateView,
    ProductDeleteView,

)

urlpatterns = [
    path('market/', MarketplaceView.as_view(), name='marketplace'),
    path('product/<int:pk>/', ProductDetailView.as_view(), name='product_detail'),
    path('store/<int:pk>/', StoreProfileView.as_view(), name='store_profile'),
    path('my-stores/', MyStoreListView.as_view(), name='store_list'),
    path('request-new/', StoreRequestCreateView.as_view(), name='store_request'),
    path('<int:pk>/manage/', StoreManageView.as_view(), name='store_manage'),
    path('<int:pk>/add-product/', ProductCreateView.as_view(), name='product_create'),
    path('<int:pk>/edit/', StoreUpdateView.as_view(), name='store_update'),
    path('product/<int:pk>/edit/', ProductUpdateView.as_view(), name='product_update'),
    path('product/<int:pk>/delete/', ProductDeleteView.as_view(), name='product_delete'),
]
