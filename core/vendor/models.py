from django.db import models
from django.contrib.auth.models import User
from products.models import Product


class Order(models.Model):

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
        ('Delivered', 'Delivered'),
    ]

    # Customer who placed the order (UNIQUE related_name)
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vendor_customer_orders'
    )

    # Vendor who receives the order (UNIQUE related_name)
    vendor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vendor_orders'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='vendor_products_orders'
    )

    quantity = models.PositiveIntegerField(default=1)

    total = models.FloatField()

    address = models.TextField()

    payment_method = models.CharField(max_length=50)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} | {self.customer.username} → {self.vendor.username}"
