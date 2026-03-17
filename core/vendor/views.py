from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from accounts.models import VendorMessage

from products.models import (
    Product, ProductVariant, VariantAttributeValue, VariantImage,
    Category, CategoryAttribute, Attribute, AttributeValue, ProductAttribute,
    Review, Sale, SaleAdvertisement, VendorSaleNotification,
)
from django.utils.text import slugify
from orders.models import Order


# =====================================================
# ROLE CHECK
# =====================================================

def is_vendor(user):
    return user.is_authenticated and user.groups.filter(name="vendor").exists()


# =====================================================
# VENDOR LOGIN
# =====================================================

def vendor_login(request):

    if request.user.is_authenticated and is_vendor(request.user):
        return redirect("vendor_dashboard")

    if request.method == "POST":

        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password")
        )

        if user and is_vendor(user):
            login(request, user)
            return redirect("vendor_dashboard")

        messages.error(request, "Invalid Vendor Credentials")

    return render(request, "vendor/login.html")


# =====================================================
# DASHBOARD
# =====================================================

@login_required
@user_passes_test(is_vendor)
def dashboard(request):

    products = Product.objects.filter(vendor=request.user)
    orders = Order.objects.filter(vendor=request.user)

    total = sum(o.total for o in orders)

    return render(request, "vendor/dashboard.html", {
        "products": products,
        "orders": orders,
        "total": total
    })


# =====================================================
# PRODUCT LIST
# =====================================================

@login_required
@user_passes_test(is_vendor)
def vendor_products(request):

    all_products = Product.objects.filter(vendor=request.user).prefetch_related("variants").order_by("-id")

    # Deduplicate: keep one entry per normalised name; prefer product with variants
    seen = {}
    for p in all_products:
        key = p.name.strip().lower()
        if key not in seen:
            seen[key] = p
        else:
            if p.variants.exists() and not seen[key].variants.exists():
                seen[key] = p

    products = list(seen.values())
    return render(request, "vendor/products.html", {"products": products})


# =====================================================
# CATEGORY TREE
# =====================================================

def build_category_tree(parent=None):

    tree = []

    for cat in Category.objects.filter(parent=parent):
        tree.append({
            "category": cat,
            "children": build_category_tree(cat)
        })

    return tree


# =====================================================
# ADD PRODUCT (PARENT)
# =====================================================

@login_required
@user_passes_test(is_vendor)
def add_product(request):

    category_tree = build_category_tree()

    if request.method == "POST":

        # ── Validate name ─────────────────────────────────────────────────
        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, "Product name is required.")
            return render(request, "vendor/add_product.html", {"category_tree": category_tree})

        # ── Safely resolve category_id ────────────────────────────────────
        # Convert empty string → None; also verify the ID actually exists
        # in the DB (guards against deleted categories or stale form data)
        raw_cat = request.POST.get("category", "").strip()
        category_id = None
        if raw_cat:
            try:
                cat_int = int(raw_cat)
                if Category.objects.filter(id=cat_int).exists():
                    category_id = cat_int
            except (ValueError, TypeError):
                pass  # non-integer value — treat as no category

        try:
            with transaction.atomic():   # <-- rolls back product row if anything below fails
                product = Product.objects.create(
                    vendor=request.user,
                    name=name,
                    brand=request.POST.get("brand", "").strip(),
                    short_description=request.POST.get("short_description", "").strip(),
                    description=request.POST.get("description", "").strip(),
                    category_id=category_id,
                    status="pending"
                )

                # Save product-level category attributes (AJAX-loaded fields on add_product page)
                for key in request.POST:
                    if key.startswith("attr_"):
                        value = request.POST.get(key, "").strip()
                        if not value:
                            continue
                        slug = key[5:]  # strip "attr_" prefix
                        try:
                            attr = Attribute.objects.get(slug=slug)
                            ProductAttribute.objects.update_or_create(
                                product=product,
                                attribute=attr,
                                defaults={"value": value},
                            )
                        except Attribute.DoesNotExist:
                            pass

                image_paths = []
                for img in request.FILES.getlist("images"):
                    path = default_storage.save(f"products/{img.name}", img)
                    image_paths.append(path)

                product.image = image_paths
                product.save()

        except Exception as e:
            messages.error(request, f"Could not save product: {e}")
            return render(request, "vendor/add_product.html", {"category_tree": category_tree})

        return redirect("vendor_add_variants", product.id)

    return render(request, "vendor/add_product.html", {
        "category_tree": category_tree
    })

# =====================================================
# ADD VARIANTS
# =====================================================



@login_required
@user_passes_test(is_vendor)
def add_variants(request, product_id):
    """
    Vendor adds a new Variant (SKU) for a Product.
    All attribute values (Color, Size, Storage, Shade …) are saved
    dynamically via VariantAttributeValue — no hardcoded columns.
    """
    product = get_object_or_404(Product, id=product_id, vendor=request.user)

    # Pull the attributes configured for this product's category
    category_attrs = CategoryAttribute.objects.filter(
        category=product.category
    ).select_related("attribute").order_by("display_order")

    if request.method == "POST":

        stock           = int(request.POST.get("stock", "0").strip() or "0")
        base_sku        = request.POST.get("sku", "").strip()
        multi_attrs_str = request.POST.get("multi_attr", "").strip()

        def _save_attrs(variant, combo_overrides=None):
            """Save all attribute values. combo_overrides = {slug: value} for multi-attrs."""
            for ca in category_attrs:
                attr  = ca.attribute
                value = (combo_overrides or {}).get(attr.slug) or \
                        request.POST.get(f"attr_{attr.slug}", "").strip()
                # For multi-attrs, take only the first comma-part if no override provided
                if value and ',' in value:
                    value = value.split(',')[0].strip()
                if value:
                    attr_val, _ = AttributeValue.objects.get_or_create(
                        attribute=attr,
                        value=value,
                        defaults={"slug": slugify(value)},
                    )
                    VariantAttributeValue.objects.get_or_create(
                        variant=variant,
                        attribute=attr,
                        defaults={"attribute_value": attr_val},
                    )

        def _save_images(variant):
            for i, img in enumerate(request.FILES.getlist("images")):
                VariantImage.objects.create(variant=variant, image=img, order=i)

        if multi_attrs_str:
            # ── MULTI-VALUE / CARTESIAN MODE ──────────────────────────────
            # multi_attrs_str  = "storage,ram"
            # combo_count      = total combos (sent as hidden input from JS)
            # price_i          = price for combo i  (blank = skip this combo)
            # stock_i          = stock for combo i
            # combo_i_<slug>   = attribute value for combo i
            multi_slugs = [s.strip() for s in multi_attrs_str.split(',') if s.strip()]
            combo_count = int(request.POST.get("combo_count", "0").strip() or "0")
            created     = 0

            for i in range(combo_count):
                price = request.POST.get(f"price_{i}", "").strip()
                if not price:
                    continue  # seller left this combo blank → skip (no DB row)

                combo_stock = int(request.POST.get(f"stock_{i}", "0").strip() or "0")

                # Build per-combo attribute overrides and SKU suffix
                combo_overrides   = {}
                combo_label_parts = []
                for slug in multi_slugs:
                    val = request.POST.get(f"combo_{i}_{slug}", "").strip()
                    combo_overrides[slug] = val
                    combo_label_parts.append(val.replace(' ', '-'))

                sku = f"{base_sku}-{'-'.join(combo_label_parts)}"

                if ProductVariant.objects.filter(sku=sku).exists():
                    messages.error(request, f"SKU '{sku}' already exists — skipped.")
                    continue

                variant = ProductVariant.objects.create(
                    product=product, price=price, stock=combo_stock, sku=sku
                )
                _save_attrs(variant, combo_overrides=combo_overrides)
                _save_images(variant)
                created += 1

            if created:
                messages.success(request, f"{created} variant(s) saved successfully.")
            else:
                messages.error(request, "No variants were created — all combinations were skipped (blank price).")

        else:
            # ── SINGLE VARIANT MODE ───────────────────────────────────────
            price = request.POST.get("price")
            sku   = base_sku

            if ProductVariant.objects.filter(sku=sku).exists():
                messages.error(request, f"SKU '{sku}' already exists. Use a unique SKU.")
                return redirect("vendor_add_variants", product.id)

            variant = ProductVariant.objects.create(
                product=product, price=price, stock=stock, sku=sku
            )
            _save_attrs(variant)
            _save_images(variant)
            messages.success(request, f"Variant '{sku}' saved successfully.")

        return redirect("vendor_add_variants", product.id)

    variants = ProductVariant.objects.filter(product=product).prefetch_related(
        "attribute_values__attribute",
        "attribute_values__attribute_value",
        "images"
    )

    return render(request, "vendor/add_variants.html", {
        "product": product,
        "variants": variants,
        "attributes": category_attrs,
    })
# =====================================================
# DELETE VARIANT
# =====================================================

@login_required
@user_passes_test(is_vendor)
def delete_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id, product__vendor=request.user)
    product_id = variant.product_id
    sku = variant.sku
    variant.delete()
    messages.success(request, f"Variant '{sku}' deleted.")
    return redirect("vendor_add_variants", product_id)


# =====================================================
# EDIT VARIANT (price / stock / sku)
# =====================================================

@login_required
@user_passes_test(is_vendor)
def edit_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id, product__vendor=request.user)
    product_id = variant.product_id

    if request.method == "POST":
        new_sku   = request.POST.get("sku", "").strip()
        new_price = request.POST.get("price", "").strip()
        new_stock = request.POST.get("stock", "0").strip()

        if new_sku and new_sku != variant.sku:
            if ProductVariant.objects.filter(sku=new_sku).exclude(pk=variant.pk).exists():
                messages.error(request, f"SKU '{new_sku}' already exists.")
                return redirect("vendor_add_variants", product_id)
            variant.sku = new_sku

        if new_price:
            variant.price = new_price
        variant.stock = int(new_stock or "0")
        variant.save()
        messages.success(request, f"Variant '{variant.sku}' updated.")

    return redirect("vendor_add_variants", product_id)


# =====================================================
# VIEW PRODUCT
# =====================================================

@login_required
@user_passes_test(is_vendor)
def vendor_view_product(request, id):

    product = get_object_or_404(Product, id=id, vendor=request.user)
    variants = ProductVariant.objects.filter(product=product).prefetch_related("images")

    return render(request, "vendor/product_detail.html", {
        "product": product,
        "variants": variants
    })


# =====================================================
# EDIT PRODUCT
# =====================================================

@login_required
@user_passes_test(is_vendor)
def edit_product(request, id):

    product = get_object_or_404(Product, id=id, vendor=request.user)
    category_tree = build_category_tree()

    if request.method == "POST":

        # ── Product fields ─────────────────────────────────
        product.name        = request.POST.get("name")
        product.description = request.POST.get("description")
        product.category_id = request.POST.get("category")
        product.status      = "pending"

        new_files = request.FILES.getlist("images")
        if new_files:
            existing = product.image or []
            for img in new_files:
                path = default_storage.save(f"products/{img.name}", img)
                existing.append(path)
            product.image = existing

        product.save()

        # ── Delete marked variant images ───────────────────
        del_ids = request.POST.getlist("delete_img")
        if del_ids:
            VariantImage.objects.filter(
                id__in=del_ids,
                variant__product=product
            ).delete()

        # ── Per-variant: update price/stock + add images ──
        for variant in product.variants.all():
            price = request.POST.get(f"vprice_{variant.id}", "").strip()
            stock = request.POST.get(f"vstock_{variant.id}", "").strip()
            if price:
                variant.price = price
            if stock:
                variant.stock = int(stock)
            variant.save()

            new_imgs = request.FILES.getlist(f"variant_images_{variant.id}")
            for i, img in enumerate(new_imgs):
                VariantImage.objects.create(variant=variant, image=img, order=i)

        messages.success(request, "Product updated.")
        return redirect("vendor_view_product", product.id)

    return render(request, "vendor/edit_product.html", {
        "product": product,
        "category_tree": category_tree,
        "all_categories": list(Category.objects.all().order_by("name")),
    })


# =====================================================
# DELETE PRODUCT
# =====================================================

@login_required
@user_passes_test(is_vendor)
def vendor_delete(request, id):

    get_object_or_404(Product, id=id, vendor=request.user).delete()
    messages.success(request, "Product deleted.")
    return redirect("vendor_products")


# =====================================================
# AJAX: VARIANT DATA (price, stock, slideshow images)
# Called when buyer clicks a variant button on product page
# URL: /vendor/variant-ajax/?variant=<id>
# =====================================================

def variant_ajax(request):

    try:
        variant = ProductVariant.objects.prefetch_related(
            "images", "attribute_values__attribute"
        ).get(id=request.GET.get("variant"))
    except ProductVariant.DoesNotExist:
        return JsonResponse({"error": "Variant not found"}, status=404)

    images = [img.image.url for img in variant.images.all()]
    attrs  = {av.attribute.slug: av.attribute_value.value for av in variant.attribute_values.all()}

    return JsonResponse({
        "price":  str(variant.price),
        "stock":  variant.stock,
        "images": images,
        "attrs":  attrs,
    })


# =====================================================
# ORDERS
# =====================================================

@login_required
@user_passes_test(is_vendor)
def vendor_orders(request):

    orders = Order.objects.filter(vendor=request.user).order_by("-id")
    return render(request, "vendor/orders.html", {
        "orders": orders,
        "status_choices": Order.STATUS_CHOICES,
    })


# =====================================================
# ACCEPT / REJECT ORDER
# =====================================================

@login_required
@user_passes_test(is_vendor)
def accept_order(request, id):

    order = get_object_or_404(Order, id=id, vendor=request.user)
    order.status = "Accepted"
    order.save()

    return redirect("vendor_orders")


@login_required
@user_passes_test(is_vendor)
def reject_order(request, id):

    order = get_object_or_404(Order, id=id, vendor=request.user)
    order.status = "Rejected"
    order.save()

    return redirect("vendor_orders")


@login_required
@user_passes_test(is_vendor)
def update_order_status(request, id):

    if request.method != "POST":
        return redirect("vendor_orders")

    order = get_object_or_404(Order, id=id, vendor=request.user)
    new_status = request.POST.get("status", "").strip()
    valid_statuses = {choice[0] for choice in Order.STATUS_CHOICES}

    if new_status in valid_statuses:
        order.status = new_status
        order.save(update_fields=["status", "updated"])
        messages.success(request, f"Order #{order.id} updated to {new_status}.")
    else:
        messages.error(request, "Invalid order status selected.")

    return redirect("vendor_orders")


# =====================================================
# PROFILE
# =====================================================

@login_required
@user_passes_test(is_vendor)
def vendor_profile(request):

    user = request.user

    if request.method == "POST":
        
        user.username = request.POST.get("username")
        user.email = request.POST.get("email")

        if request.POST.get("password"):
            user.set_password(request.POST.get("password"))

        user.save()

        return redirect("vendor_profile")

    return render(request, "vendor/profile.html", {"user": user})

# =====================================================
# AJAX: GET ATTRIBUTES FOR A CATEGORY
# URL: /vendor/get-category-attributes/?category=<id>
# Returns JSON list used to dynamically render form inputs
# =====================================================

def get_category_attributes(request):

    cid = request.GET.get("category")

    rows = CategoryAttribute.objects.filter(
        category_id=cid
    ).select_related("attribute").order_by("display_order")

    data = []

    for r in rows:
        data.append({
            "slug":        r.attribute.slug,
            "name":        r.attribute.name,
            "type":        r.attribute.input_type,
            "is_required": r.is_required,
            "values":      list(r.attribute.values.values_list("value", flat=True)),
        })

    return JsonResponse(data, safe=False)


# =====================================================
# VENDOR INBOX  (chat with admin)
# =====================================================

@login_required
@user_passes_test(is_vendor)
def vendor_inbox(request):
    """Vendor sees all messages from admin and can reply."""

    if request.method == 'POST':
        msg_text = request.POST.get('message', '').strip()
        if msg_text:
            VendorMessage.objects.create(
                vendor=request.user,
                sender=request.user,
                message=msg_text
            )
        return redirect('vendor_inbox')

    # Mark admin messages as read
    VendorMessage.objects.filter(
        vendor=request.user,
        is_read=False
    ).exclude(sender=request.user).update(is_read=True)

    msgs = VendorMessage.objects.filter(vendor=request.user).select_related('sender')

    return render(request, 'vendor/vendor_inbox.html', {
        'messages': msgs
    })


# =====================================================
# VENDOR ANALYTICS
# =====================================================

import json as _json
from datetime import date
from dateutil.relativedelta import relativedelta

@login_required
@user_passes_test(is_vendor)
def vendor_analytics(request):
    import calendar

    products   = Product.objects.filter(vendor=request.user)
    product_ids = list(products.values_list('id', flat=True))
    orders     = Order.objects.filter(vendor=request.user)

    # ── KPI cards ──────────────────────────────────────────────────
    total_revenue   = orders.aggregate(s=Sum('total'))['s'] or 0
    total_orders    = orders.count()
    total_products  = products.count()
    avg_order_value = round(total_revenue / total_orders, 2) if total_orders else 0

    # ── Revenue last 6 months ──────────────────────────────────────
    today = date.today()
    month_labels, month_revenue = [], []
    for i in range(5, -1, -1):
        d = today.replace(day=1) - relativedelta(months=i)
        label = d.strftime('%b %Y')
        rev = orders.filter(
            created__year=d.year,
            created__month=d.month
        ).aggregate(s=Sum('total'))['s'] or 0
        month_labels.append(label)
        month_revenue.append(round(float(rev), 2))

    # ── Orders by status ──────────────────────────────────────────
    status_data = (
        orders.values('status')
              .annotate(cnt=Count('id'))
              .order_by('status')
    )
    status_labels  = [x['status'] for x in status_data]
    status_counts  = [x['cnt']    for x in status_data]

    # ── Top 5 products by revenue ─────────────────────────────────
    top_products = (
        orders.values('product__name')
              .annotate(rev=Sum('total'), cnt=Count('id'))
              .order_by('-rev')[:5]
    )
    top_names   = [x['product__name'] for x in top_products]
    top_rev     = [round(float(x['rev']), 2) for x in top_products]

    # ── Reviews summary ───────────────────────────────────────────
    reviews = Review.objects.filter(product__in=products, approved=True)
    total_reviews = reviews.count()
    avg_rating    = round(reviews.aggregate(a=Avg('rating'))['a'] or 0, 1)
    rating_dist   = {i: reviews.filter(rating=i).count() for i in range(5, 0, -1)}

    return render(request, 'vendor/analytics.html', {
        'total_revenue':   total_revenue,
        'total_orders':    total_orders,
        'total_products':  total_products,
        'avg_order_value': avg_order_value,
        'total_reviews':   total_reviews,
        'avg_rating':      avg_rating,
        'rating_dist':     rating_dist,
        # JSON for charts
        'month_labels_json':  _json.dumps(month_labels),
        'month_revenue_json': _json.dumps(month_revenue),
        'status_labels_json': _json.dumps(status_labels),
        'status_counts_json': _json.dumps(status_counts),
        'top_names_json':     _json.dumps(top_names),
        'top_rev_json':       _json.dumps(top_rev),
    })


# =====================================================
# VENDOR REVIEWS
# =====================================================

@login_required(login_url="/vendor/login/")
@user_passes_test(is_vendor, login_url="/vendor/login/")
def vendor_reviews(request):
    status_filter = request.GET.get("status", "pending")

    base_qs = Review.objects.filter(
        product__vendor=request.user
    ).select_related("product", "user").prefetch_related("extra_images").order_by("-created")

    if status_filter == "approved":
        reviews_qs = base_qs.filter(approved=True)
    else:
        reviews_qs = base_qs.filter(approved=False)

    total_pending  = base_qs.filter(approved=False).count()
    total_approved = base_qs.filter(approved=True).count()

    return render(request, "vendor/reviews.html", {
        "reviews": reviews_qs,
        "status_filter": status_filter,
        "total_pending": total_pending,
        "total_approved": total_approved,
    })


@login_required(login_url="/vendor/login/")
@user_passes_test(is_vendor, login_url="/vendor/login/")
def vendor_review_action(request):
    if request.method != "POST":
        return redirect("vendor_reviews")
    action    = request.POST.get("action")
    review_id = request.POST.get("review_id")
    review = get_object_or_404(Review, id=review_id, product__vendor=request.user)
    if action == "approve":
        review.approved = True
        review.save()
        messages.success(request, "Review approved and is now visible to customers.")
    elif action == "reject":
        review.approved = False
        review.save()
        messages.success(request, "Review hidden from customers.")
    elif action == "delete":
        review.delete()
        messages.success(request, "Review deleted.")
    return redirect(f"/vendor/reviews/?status={request.POST.get('status_filter', 'pending')}")


# =====================================================
# VENDOR SALES
# =====================================================

@login_required(login_url="/vendor/login/")
@user_passes_test(is_vendor, login_url="/vendor/login/")
def vendor_sales(request):
    now = timezone.now()
    # Mark all unread notifications as read on viewing
    VendorSaleNotification.objects.filter(vendor=request.user, is_read=False).update(is_read=True)

    notifications = VendorSaleNotification.objects.filter(vendor=request.user).select_related("sale").order_by("-created_at")
    active_sales = Sale.objects.filter(is_active=True, end_datetime__gte=now).order_by("start_datetime")
    my_ads = SaleAdvertisement.objects.filter(vendor=request.user).select_related("sale", "product")

    # Build a set of (sale_id, product_id) already submitted
    submitted_keys = set(my_ads.values_list("sale_id", "product_id"))

    return render(request, "vendor/vendor_sales.html", {
        "notifications": notifications,
        "active_sales": active_sales,
        "my_ads": my_ads,
        "submitted_keys": submitted_keys,
    })


@login_required(login_url="/vendor/login/")
@user_passes_test(is_vendor, login_url="/vendor/login/")
def vendor_submit_ad(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id, is_active=True)
    vendor_products = Product.objects.filter(vendor=request.user, status="approved")
    categories = Category.objects.all().order_by("name")

    if request.method == "POST":
        product_type = request.POST.get("product_type", "existing")
        ad_image = request.FILES.get("ad_image")
        note = request.POST.get("note", "").strip()
        sale_price = request.POST.get("sale_price", "").strip()
        quantity = request.POST.get("quantity", "").strip()

        if not ad_image:
            messages.error(request, "Please upload an ad image.")
            return redirect("vendor_submit_ad", sale_id=sale_id)

        if not sale_price or not quantity:
            messages.error(request, "Please enter both sale price and quantity.")
            return redirect("vendor_submit_ad", sale_id=sale_id)

        if product_type == "new":
            new_name = request.POST.get("new_name", "").strip()
            new_description = request.POST.get("new_description", "").strip()
            new_category_id = request.POST.get("new_category", "").strip()

            if not new_name:
                messages.error(request, "Please enter a name for the new product.")
                return redirect("vendor_submit_ad", sale_id=sale_id)

            product = Product.objects.create(
                vendor=request.user,
                name=new_name,
                description=new_description,
                category_id=new_category_id if new_category_id else None,
                status="pending",
            )
        else:
            product_id = request.POST.get("product_id")
            if not product_id:
                messages.error(request, "Please select a product.")
                return redirect("vendor_submit_ad", sale_id=sale_id)
            product = get_object_or_404(Product, id=product_id, vendor=request.user)

        # Check if already submitted for this sale+product combo
        if SaleAdvertisement.objects.filter(sale=sale, vendor=request.user, product=product).exists():
            messages.warning(request, "You have already submitted an ad for this product in this sale.")
            return redirect("vendor_sales")

        SaleAdvertisement.objects.create(
            sale=sale,
            vendor=request.user,
            product=product,
            ad_image=ad_image,
            sale_price=sale_price,
            quantity=quantity,
            note=note,
            is_approved=False,
        )
        msg = "Ad submitted! Your new product is pending admin approval." if product_type == "new" else "Ad submitted successfully! It will appear once approved by admin."
        messages.success(request, msg)
        return redirect("vendor_sales")

    return render(request, "vendor/vendor_sale_submit.html", {
        "sale": sale,
        "vendor_products": vendor_products,
        "categories": categories,
    })
