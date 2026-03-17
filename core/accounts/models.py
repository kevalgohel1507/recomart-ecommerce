from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):

    ROLE_CHOICES = (
        ("customer","Customer"),
        ("vendor","Vendor"),
    )

    user = models.OneToOneField(User,on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True, null=True)

    role = models.CharField(max_length=20,choices=ROLE_CHOICES)

    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


class VendorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    shop_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15)
    address = models.TextField()

    profile_pic = models.ImageField(upload_to='vendors/', blank=True, null=True)

    joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.shop_name


class GuestLocation(models.Model):
    """Stores location captured from unauthenticated (guest) visitors."""

    SOURCE_CHOICES = (
        ('gps',    'GPS / Browser'),
        ('ip',     'IP Geolocation'),
        ('manual', 'Manual Entry'),
    )

    session_key = models.CharField(max_length=40, blank=True, null=True)
    ip_address  = models.GenericIPAddressField(blank=True, null=True)
    latitude    = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude   = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    city        = models.CharField(max_length=120, blank=True, null=True)
    state       = models.CharField(max_length=120, blank=True, null=True)
    country     = models.CharField(max_length=100, blank=True, null=True)
    source      = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='gps')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Guest [{self.source}] {self.session_key or self.ip_address} — {self.city or ''}, {self.country or ''}"


class VendorMessage(models.Model):
    """Chat messages between admin and a vendor."""

    vendor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vendor_messages'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_vendor_messages'
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username} → vendor {self.vendor.username}: {self.message[:40]}"