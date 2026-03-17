from django.contrib import admin
from .models import (
    Category,
    Attribute,
    AttributeValue,
    CategoryAttribute,
    Product,
    ProductVariant,
    VariantAttributeValue,
    VariantImage,
    Review,
    ReviewImage,
    Bundle,
    BundleProduct,
)


# =============================
# INLINE ADMINS
# =============================

class VariantImageInline(admin.TabularInline):
    model = VariantImage
    extra = 1
    fields = ("image", "order")


class VariantAttributeValueInline(admin.TabularInline):
    model = VariantAttributeValue
    extra = 1
    fields = ("attribute", "attribute_value")   # ✅ FIXED


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("sku", "price", "stock")
    show_change_link = True


class BundleProductInline(admin.TabularInline):
    model = BundleProduct
    extra = 1
    fields = ("product", "discounted_price")
    autocomplete_fields = ("product",)


# =============================
# PRODUCT ADMIN
# =============================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "vendor",
        "category",
        "status",
        "is_active",
    )

    list_filter = ("status", "is_active", "category")
    search_fields = ("name", "vendor__username")
    readonly_fields = ("slug",)

    inlines = [ProductVariantInline]

    fieldsets = (
        ("Basic Info", {
            "fields": (
                "vendor",
                "name",
                "slug",
                "category",
                "brand",
                "short_description",
                "description",
                "image",  # ✅ FIXED (was preview_images)
            )
        }),

        ("Status", {
            "fields": (
                "status",
                "is_active",
            )
        }),
    )

    actions = ["approve_products", "reject_products"]

    def approve_products(self, request, queryset):
        queryset.update(status="approved", is_active=True)
        self.message_user(request, f"{queryset.count()} products approved.")

    approve_products.short_description = "Approve Selected Products"

    def reject_products(self, request, queryset):
        queryset.update(status="rejected", is_active=False)
        self.message_user(request, f"{queryset.count()} products rejected.")

    reject_products.short_description = "Reject Selected Products"


# =============================
# BUNDLE ADMIN
# =============================

@admin.register(Bundle)
class BundleAdmin(admin.ModelAdmin):
    list_display = ("name", "bundle_price", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    inlines = [BundleProductInline]


# =============================
# PRODUCT VARIANT ADMIN
# =============================

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):

    list_display = ("product", "sku", "price", "stock", "display_attrs")
    search_fields = ("product__name", "sku")

    inlines = [VariantAttributeValueInline, VariantImageInline]

    @admin.display(description="Attributes")
    def display_attrs(self, obj):
        return obj.display_attributes()


# =============================
# CATEGORY ADMIN
# =============================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


# =============================
# ATTRIBUTE ADMIN
# =============================

@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "input_type",
        "is_required",
        "is_filterable",
    )

    list_filter = ("input_type", "is_required", "is_filterable")
    search_fields = ("name",)
    readonly_fields = ("slug",)


# =============================
# ATTRIBUTE VALUE ADMIN (NEW)
# =============================

@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):

    list_display = ("attribute", "value", "slug")
    list_filter = ("attribute",)
    search_fields = ("value",)


# =============================
# CATEGORY ATTRIBUTE ADMIN
# =============================

@admin.register(CategoryAttribute)
class CategoryAttributeAdmin(admin.ModelAdmin):

    list_display = ("category", "attribute", "is_required", "display_order")
    list_filter = ("category",)
    ordering = ("display_order",)


# =============================
# VARIANT ATTRIBUTE VALUE ADMIN
# =============================

@admin.register(VariantAttributeValue)
class VariantAttributeValueAdmin(admin.ModelAdmin):

    list_display = ("variant", "attribute", "get_value")
    list_filter = ("attribute",)
    search_fields = ("variant__sku", "attribute__name", "attribute_value__value")

    @admin.display(description="Value")
    def get_value(self, obj):
        return obj.attribute_value.value


# =============================
# REVIEW IMAGE INLINE
# =============================

class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 0
    fields = ("image", "order")
    readonly_fields = ("image",)


# =============================
# REVIEW ADMIN
# =============================

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):

    list_display = ("product", "user", "rating", "approved", "created")
    list_filter = ("approved", "rating")
    search_fields = ("product__name", "user__username")
    list_editable = ("approved",)
    readonly_fields = ("product", "user", "rating", "comment", "image", "created")

    inlines = [ReviewImageInline]

    actions = ["approve_reviews", "reject_reviews"]

    def approve_reviews(self, request, queryset):
        queryset.update(approved=True)
        self.message_user(request, f"{queryset.count()} review(s) approved and now visible to customers.")

    approve_reviews.short_description = "Approve selected reviews"

    def reject_reviews(self, request, queryset):
        queryset.update(approved=False)
        self.message_user(request, f"{queryset.count()} review(s) hidden/rejected.")

    reject_reviews.short_description = "Reject / hide selected reviews"


@admin.register(ReviewImage)
class ReviewImageAdmin(admin.ModelAdmin):
    list_display = ("review", "image", "order")
    list_filter = ("review__approved",)