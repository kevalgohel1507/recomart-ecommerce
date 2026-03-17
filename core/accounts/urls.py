from django.urls import path
from . import views

urlpatterns = [
    path('login/',              views.login_view,          name='login'),
    path('register/',           views.register,            name='register'),
    path('logout/',             views.logout_view,         name='logout'),
    path('profile/',            views.profile,             name='profile'),
    path('admin-dashboard/',    views.admin_dashboard,     name='admin_dashboard'),
    path('send-email-otp/',     views.send_email_otp,      name='send_email_otp'),
    path('verify-email-otp/',   views.verify_email_otp,    name='verify_email_otp'),
    path('send-phone-otp/',     views.send_phone_otp,      name='send_phone_otp'),
    path('verify-phone-otp/',   views.verify_phone_otp,    name='verify_phone_otp'),
    path('save-location/',      views.save_guest_location, name='save_guest_location'),
]
