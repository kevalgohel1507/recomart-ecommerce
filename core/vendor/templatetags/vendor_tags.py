from django import template
from products.models import VendorSaleNotification, Sale
from django.utils import timezone

register = template.Library()


@register.simple_tag
def vendor_unread_sale_notifs(user):
    """Return the count of unread sale notifications for a vendor."""
    if not user or not user.is_authenticated:
        return 0
    return VendorSaleNotification.objects.filter(vendor=user, is_read=False).count()


@register.simple_tag
def active_or_upcoming_sale():
    """Return the nearest active or upcoming sale, or None."""
    now = timezone.now()
    return (
        Sale.objects.filter(is_active=True, end_datetime__gte=now)
        .order_by('start_datetime')
        .first()
    )
