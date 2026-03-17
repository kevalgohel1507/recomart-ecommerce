from django.urls import path
from . import views

urlpatterns = [
    path('my-orders/', views.my_orders, name='my_orders'),
    path('cancel/', views.cancel_order, name='cancel_order'),
    path('bill/', views.order_bill, name='order_bill'),
    path('create-razorpay-order/', views.create_razorpay_order, name='create_razorpay_order'),
    path('razorpay-success/', views.razorpay_payment_success, name='razorpay_payment_success'),
]