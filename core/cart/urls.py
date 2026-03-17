from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart_view, name='cart'),

    path('add/<int:id>/', views.add_cart, name='add_cart'),
    path('add-bundle/', views.add_bundle_to_cart, name='add_bundle_to_cart'),
    path('remove/<int:id>/', views.remove_cart, name='remove_cart'),
    path('update/', views.update_cart, name='update_cart'),

    # checkout flow
    path('checkout/address/', views.checkout_address, name='checkout_address'),
    path('checkout/', views.checkout, name='checkout'),

    path('success/', views.order_success, name='order_success'),
]