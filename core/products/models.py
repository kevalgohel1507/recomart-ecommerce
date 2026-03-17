from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

# =====================================================
# CATEGORY
# =====================================================

class Category(models.Model):

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True, null=True)

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children"
    )

    icon = models.ImageField(upload_to="category_icons/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            i = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# =====================================================
# ATTRIBUTE MASTER
# =====================================================

class Attribute(models.Model):

    INPUT_TYPE_CHOICES = (
        ("text", "Text"),
        ("number", "Number"),
        ("select", "Dropdown"),
        ("radio", "Radio"),
        ("checkbox", "Checkbox"),
    )

    SECTION_CHOICES = (
        ("specs", "Specifications"),
        ("manufacturer", "Manufacturer Info"),
    )

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True, null=True)

    input_type = models.CharField(max_length=20, choices=INPUT_TYPE_CHOICES, default="text")
    section = models.CharField(max_length=30, choices=SECTION_CHOICES, default="specs")
    is_required = models.BooleanField(default=False)
    is_filterable = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# =====================================================
# ATTRIBUTE VALUES (ADMIN CONTROLLED)
# Example: Color → Red, Blue
# =====================================================

class AttributeValue(models.Model):

    attribute = models.ForeignKey(Attribute, related_name="values", on_delete=models.CASCADE)
    value = models.CharField(max_length=100)
    slug = models.SlugField(blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.value)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


# =====================================================
# CATEGORY ↔ ATTRIBUTE MAPPING
# =====================================================

class CategoryAttribute(models.Model):

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="category_attributes")
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE)

    is_required = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("category", "attribute")
        ordering = ["display_order"]

    def __str__(self):
        return f"{self.category.name} → {self.attribute.name}"


# =====================================================
# PRODUCT
# =====================================================

class Product(models.Model):

    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)

    brand = models.CharField(max_length=100, blank=True)
    short_description = models.TextField(blank=True)
    description = models.TextField()

    # Manufacturer / compliance info
    generic_name          = models.CharField(max_length=255, blank=True)
    country_of_origin     = models.CharField(max_length=100, blank=True)
    manufacturer_address  = models.TextField(blank=True)
    packer_address        = models.TextField(blank=True)

    image = models.JSONField(default=list, blank=True)

    status = models.CharField(max_length=30, default="pending")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            i = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# =====================================================
# PRODUCT VARIANT (SELLABLE SKU)
# =====================================================

class ProductVariant(models.Model):

    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)

    sku   = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    mrp   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                help_text="MRP / original price before discount")
    stock = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} — SKU: {self.sku}"

    def get_attribute_value(self, attribute_slug):
        try:
            return self.attribute_values.get(attribute__slug=attribute_slug).attribute_value.value
        except VariantAttributeValue.DoesNotExist:
            return None

    def display_attributes(self):
        pairs = self.attribute_values.select_related("attribute", "attribute_value").all()
        return " | ".join(f"{p.attribute.name}: {p.attribute_value.value}" for p in pairs)


# =====================================================
# VARIANT ATTRIBUTE VALUE (NORMALIZED)
# =====================================================

class VariantAttributeValue(models.Model):

    variant = models.ForeignKey(
        ProductVariant,
        related_name="attribute_values",
        on_delete=models.CASCADE
    )

    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE
    )

    attribute_value = models.ForeignKey(
        AttributeValue,
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("variant", "attribute")

    @property
    def value(self):
        """Shortcut so templates and views can use av.value directly."""
        return self.attribute_value.value

    def __str__(self):
        return f"{self.variant.sku} | {self.attribute.name}: {self.attribute_value.value}"


# =====================================================
# VARIANT IMAGE
# =====================================================

class VariantImage(models.Model):

    variant = models.ForeignKey(ProductVariant, related_name="images", on_delete=models.CASCADE)
    image   = models.ImageField(upload_to="products/variants/")
    order   = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Image for {self.variant.sku}"


# =====================================================
# REVIEWS
# =====================================================

class Review(models.Model):

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user    = models.ForeignKey(User, on_delete=models.CASCADE)

    rating   = models.IntegerField(default=5)
    comment  = models.TextField()
    image    = models.ImageField(upload_to="reviews/", blank=True, null=True)
    approved = models.BooleanField(default=False)
    created  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} — {self.user.username}"


# =====================================================
# REVIEW IMAGES (multiple per review)
# =====================================================

class ReviewImage(models.Model):

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="extra_images")
    image  = models.ImageField(upload_to="reviews/")
    order  = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Image for review #{self.review.id}"


# =====================================================
# LEGACY PRODUCT ATTRIBUTE (OPTIONAL)
# =====================================================

class ProductAttribute(models.Model):

    product   = models.ForeignKey(Product, related_name="attributes", on_delete=models.CASCADE)
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE)
    value     = models.CharField(max_length=255)

    class Meta:
        unique_together = ("product", "attribute")

    def __str__(self):
        return f"{self.product.name} | {self.attribute.name}: {self.value}"


# =====================================================
# SALE EVENT (admin creates)
# =====================================================

class Sale(models.Model):

    title          = models.CharField(max_length=200)
    description    = models.TextField(blank=True)
    banner_text    = models.CharField(max_length=255, blank=True)
    start_datetime = models.DateTimeField()
    end_datetime   = models.DateTimeField()
    is_active      = models.BooleanField(default=False)
    created_by     = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_sales")
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def is_live(self):
        from django.utils import timezone
        now = timezone.now()
        return self.is_active and self.start_datetime <= now <= self.end_datetime

    @property
    def is_upcoming(self):
        from django.utils import timezone
        return self.is_active and timezone.now() < self.start_datetime


# =====================================================
# VENDOR SALE AD (vendor submits for a sale)
# =====================================================

class SaleAdvertisement(models.Model):

    sale      = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="advertisements")
    vendor    = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sale_ads")
    product   = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sale_ads")
    ad_image  = models.ImageField(upload_to="sale_ads/")
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Your sale price for this product")
    quantity   = models.PositiveIntegerField(default=1, help_text="Stock available for this sale")
    note      = models.TextField(blank=True, help_text="Optional message to admin")
    is_approved = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("sale", "vendor", "product")

    def __str__(self):
        return f"{self.vendor.username} — {self.product.name} [{self.sale.title}]"


# =====================================================
# VENDOR SALE NOTIFICATION
# =====================================================

class VendorSaleNotification(models.Model):

    sale       = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="vendor_notifications")
    vendor     = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sale_notifications")
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("sale", "vendor")

    def __str__(self):
        return f"Notif → {self.vendor.username} | {self.sale.title}"


class UserProductInteraction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey("Product", on_delete=models.CASCADE)
    interaction_type = models.CharField(max_length=20)  
    # view, cart, purchase, rating
    created_at = models.DateTimeField(auto_now_add=True)

class ProductRelation(models.Model):

    product = models.ForeignKey(
        Product,
        related_name="cross_products",
        on_delete=models.CASCADE
    )

    related_product = models.ForeignKey(
        Product,
        related_name="related_to",
        on_delete=models.CASCADE
    )

    score = models.FloatField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product", "related_product")

    def __str__(self):
        return f"{self.product.name} -> {self.related_product.name}"


# =====================================================
# PRODUCT BUNDLE
# =====================================================

class Bundle(models.Model):

    name = models.CharField(max_length=200)
    products = models.ManyToManyField(
        Product,
        related_name="bundles",
        through="BundleProduct",
    )
    bundle_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class BundleProduct(models.Model):
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE, related_name="bundle_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="bundle_items")
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "products_bundle_products"
        unique_together = ("bundle", "product")

    def __str__(self):
        return f"{self.bundle.name} -> {self.product.name}"


# =====================================================
# SEARCH QUERY LOG  (NLP autocomplete trending data)
# =====================================================

class SearchQuery(models.Model):
    """Records every search for trending analysis and recommendation."""

    query       = models.CharField(max_length=255, db_index=True)
    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    results_count = models.PositiveIntegerField(default=0)
    timestamp   = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["query", "timestamp"]),
        ]

    def __str__(self):
        return f'"{self.query}" @ {self.timestamp:%Y-%m-%d %H:%M}'