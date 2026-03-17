from django.contrib import admin
from .models import UserProfile

admin.site.register(UserProfile)

from .models import VendorProfile
admin.site.register(VendorProfile)
