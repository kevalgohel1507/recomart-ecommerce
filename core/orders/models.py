from django.db import models
from django.contrib.auth.models import User
from products.models import Product, ProductVariant


class Order(models.Model):

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Accepted", "Accepted"),
        ("Packed", "Packed"),
        ("Out for Delivery", "Out for Delivery"),
        ("Shipped", "Shipped"),
        ("Delivered", "Delivered"),
        ("Cancelled", "Cancelled"),
        ("Rejected", "Rejected"),
    ]

    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="customer_orders"
    )

    vendor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="vendor_received_orders"  # ✅ UNIQUE NAME
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)

    quantity = models.PositiveIntegerField(default=1)
    total = models.FloatField()
    platform_fee = models.FloatField(default=0.0)
    platform_fee_gst = models.FloatField(default=0.0)
    vendor_profit = models.FloatField(default=0.0)

    address = models.TextField()
    pincode = models.CharField(max_length=6)

    payment_method = models.CharField(max_length=50)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    cancel_reason = models.CharField(max_length=200, blank=True, default="")
    cancel_note   = models.TextField(blank=True, default="")

    # Razorpay payment details
    razorpay_order_id   = models.CharField(max_length=100, blank=True, default="")
    razorpay_payment_id = models.CharField(max_length=100, blank=True, default="")
    payment_status      = models.CharField(max_length=20, default="Pending")  # Pending / Paid / Failed

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    # ── Per-item price helpers (single-item use only) ────────────────
    # For multi-item checkouts, use the group totals computed in orders/views.py
    SHIPPING = 40.0
    PLATFORM_FEE_PCT = 0.12
    GST_PCT = 0.18
    ADMIN_CUT_PCT = 0.30

    @property
    def gst_amount(self):
        return round(self.platform_fee_gst, 2)

    @property
    def final_total(self):
        return round(self.total + self.platform_fee + self.gst_amount + self.SHIPPING, 2)

    @property
    def admin_cut_amount(self):
        return round(self.platform_fee + self.platform_fee_gst, 2)

    @property
    def vendor_profit_amount(self):
        return round(self.vendor_profit, 2)

    def __str__(self):
        return f"{self.product.name} | {self.customer.username}"
