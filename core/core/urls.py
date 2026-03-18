from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('vendor/', include('vendor.urls')),
    path('', include('products.urls')),
    path('accounts/', include('accounts.urls')),
    path('auth/', include('allauth.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path('adminpanel/', include('adminpanel.urls')),
    path('accounts/change-password/', auth_views.PasswordChangeView.as_view(
    template_name='accounts/change_password.html',
    success_url='/accounts/profile/'
    
)),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
