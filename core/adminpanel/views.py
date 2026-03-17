from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import messages
from decimal import Decimal, InvalidOperation

from products.models import BundleProduct
from django.core.paginator import Paginator
from products.models import Product

from orders.models import Order
from products.models import (
    Product,
    Category,
    ProductAttribute,
    Attribute,
    CategoryAttribute,
    ProductVariant,
    Review,
    Sale,
    SaleAdvertisement,
    VendorSaleNotification,
    Bundle,
)
from accounts.models import VendorProfile, VendorMessage
from django.contrib.auth.models import Group
from django.utils import timezone

# ================= ROLE CHECK =================

def is_admin(user):
    return user.is_superuser or user.groups.filter(name="admin").exists()

# ================= CATEGORY TREE HELPER =================

def build_category_tree(parent=None, depth=0):
    """Return a flat depth-first list of dicts {'cat': obj, 'indent': str}."""
    tree = []
    for cat in Category.objects.filter(parent=parent).order_by('name'):
        tree.append({'cat': cat, 'indent': '\u2014' * depth})
        tree.extend(build_category_tree(parent=cat, depth=depth + 1))
    return tree

# ================= ADMIN LOGIN =================

def admin_login(request):

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user and is_admin(user):
            login(request, user)
            return redirect("adminpanel:admin_dashboard")

        messages.error(request, "Invalid credentials")

    return render(request, "adminpanel/login.html")

# ================= DASHBOARD =================

@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def admin_dashboard(request):

    return render(request, "adminpanel/dashboard.html", {
        "products": Product.objects.count(),
        "orders": Order.objects.count(),
        "users": User.objects.count(),
        "categories": Category.objects.count(),
        "recent_orders": Order.objects.select_related("customer").order_by("-id")[:8],
        "recent_users": User.objects.order_by("-date_joined")[:6],
        "low_stock": ProductVariant.objects.filter(stock__lte=5).select_related("product").order_by("stock")[:6],
    })

# ================= CATEGORIES =================

@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def categories(request):

    categories = Category.objects.all()
    attributes = Attribute.objects.all()

    if request.method == "POST":

        if "add_category" in request.POST:
            Category.objects.create(
                name=request.POST.get("name"),
                parent_id=request.POST.get("parent") or None,
                icon=request.FILES.get("icon")
            )
            messages.success(request, "Category added")
            return redirect("adminpanel:categories")

        if "add_attribute" in request.POST:
            name = request.POST.get("attribute")
            section = request.POST.get("attr_section", "specs")
            if name:
                Attribute.objects.create(name=name, section=section)
                messages.success(request, "Attribute added")
            return redirect("adminpanel:categories")

    return render(request, "adminpanel/categories.html", {
        "categories": categories,
        "attributes": attributes,
        "category_tree": build_category_tree(),
    })

@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def edit_category(request, id):

    category = get_object_or_404(Category, id=id)

    if request.method == "POST":
        category.name = request.POST.get("name")
        category.parent_id = request.POST.get("parent") or None

        if request.FILES.get("icon"):
            category.icon = request.FILES.get("icon")

        category.save()
        messages.success(request, "Category updated")
        return redirect("adminpanel:categories")

    return render(request, "adminpanel/edit_category.html", {
        "category": category,
        "all_categories": Category.objects.exclude(id=id),
        "category_tree": build_category_tree(),
    })

@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def delete_category(request, id):
    Category.objects.filter(id=id).delete()
    messages.success(request, "Category deleted")
    return redirect("adminpanel:categories")

# ================= CATEGORY ATTRIBUTE MAPPING =================

@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def category_attributes_page(request):

    categories = Category.objects.all()
    attributes = Attribute.objects.all()

    selected_category = None
    selected_attribute_ids = []

    # GET selected category
    category_id = request.GET.get("category")

    if category_id:
        selected_category = get_object_or_404(Category, id=category_id)
        selected_attribute_ids = list(
            CategoryAttribute.objects.filter(category=selected_category)
            .values_list("attribute_id", flat=True)
        )

    # ================= SAVE ONLY ON POST =================

    if request.method == "POST":

        category_id = request.POST.get("category")

        if not category_id:
            messages.error(request, "Category missing.")
            return redirect(request.path)

        attribute_ids = request.POST.getlist("attributes")

        # CLEAR OLD
        CategoryAttribute.objects.filter(category_id=category_id).delete()

        # SAVE NEW
        for attr_id in attribute_ids:
            CategoryAttribute.objects.create(
                category_id=category_id,
                attribute_id=attr_id
            )

        # ✅ MESSAGE ONLY HERE
        messages.success(request, "Mapping saved successfully ✔")

        # redirect AFTER save
        return redirect(f"/adminpanel/category-attributes/?category={category_id}")

    # ======================================================

    return render(request, "adminpanel/category_attributes.html", {
        "categories": categories,
        "attributes": attributes,
        "selected_category": selected_category,
        "selected_attribute_ids": selected_attribute_ids
    })

# ================= PRODUCTS =================

@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def admin_products(request):

    # Order: products with variants (price set) first, then by latest
    all_products = Product.objects.prefetch_related('variants').order_by("-created_at")

    # Deduplicate: keep one entry per (vendor_id, normalised name)
    # Priority: the one that already has variants over blank stubs created during errors
    seen = {}
    for p in all_products:
        key = (p.vendor_id, p.name.strip().lower())
        if key not in seen:
            seen[key] = p
        else:
            # Prefer the product that has at least one variant
            if p.variants.exists() and not seen[key].variants.exists():
                seen[key] = p

    products = list(seen.values())

    return render(request, "adminpanel/products.html", {
        "products": products
    })

@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def toggle_product_status(request, id):

    product = get_object_or_404(Product, id=id)
    product.status = "approved" if product.status != "approved" else "pending"
    product.save()

    messages.success(request, "Product status updated")
    return redirect("adminpanel:admin_products")

@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def product_detail(request, id):

    product = get_object_or_404(Product, id=id)
    variants = product.variants.prefetch_related(
        "images",
        "attribute_values__attribute",
        "attribute_values__attribute_value"
    ).all()

    return render(request, "adminpanel/product_detail.html", {
        "product":  product,
        "variants": variants,
    })

@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def delete_product(request, id):
    Product.objects.filter(id=id).delete()
    messages.success(request, "Product deleted")
    return redirect("adminpanel:admin_products")

# ================= ORDERS =================

@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def orders(request):

    orders = Order.objects.all()

    return render(request, "adminpanel/orders.html", {
        "orders": orders
    })

# ================= USERS =================

@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def users(request):

    return render(request, "adminpanel/users.html", {
        "users": User.objects.all()
    })

@login_required
def edit_product(request, id):
    product = get_object_or_404(Product, id=id)

    if request.method == "POST":
        product.name = request.POST.get("name")
        product.price = request.POST.get("price")
        product.description = request.POST.get("description")

        # Save new uploaded images into JSON list
        from django.core.files.storage import default_storage

        new_files = request.FILES.getlist("images")
        if new_files:
            existing = product.image if isinstance(product.image, list) else []
            for img in new_files:
                path = default_storage.save(f"products/{img.name}", img)
                existing.append(path)
            product.image = existing

        product.save()

        return redirect("admin_product_detail", id=product.id)

    return render(request, "adminpanel/edit_product.html", {
        "product": product
    })
@login_required
def approve_product(request, id):

    product = get_object_or_404(Product, id=id)
    product.status = "approved"
    product.save()

    messages.success(request, "Product approved successfully.")

    return redirect("admin_products")

# ================= VENDORS =================

@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def vendor_list(request):
    """Show all users who registered as vendors."""
    vendor_users = User.objects.filter(groups__name='vendor').select_related('vendorprofile').order_by('date_joined')
    return render(request, 'adminpanel/vendors.html', {
        'vendor_users': vendor_users
    })


@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def vendor_chat(request, vendor_id):
    """Admin ↔ Vendor chat page."""
    vendor = get_object_or_404(User, id=vendor_id, groups__name='vendor')

    if request.method == 'POST':
        msg_text = request.POST.get('message', '').strip()
        if msg_text:
            VendorMessage.objects.create(
                vendor=vendor,
                sender=request.user,
                message=msg_text
            )
        return redirect('adminpanel:vendor_chat', vendor_id=vendor_id)

    # Mark vendor messages to admin as read
    VendorMessage.objects.filter(vendor=vendor, is_read=False).exclude(sender=request.user).update(is_read=True)

    messages_qs = VendorMessage.objects.filter(vendor=vendor).select_related('sender')
    return render(request, 'adminpanel/vendor_chat.html', {
        'vendor': vendor,
        'messages': messages_qs
    })


#  edit and delete attribute views
def edit_attribute(request, id):

    attribute = get_object_or_404(Attribute, id=id)

    if request.method == "POST":
        name = request.POST.get("name")
        section = request.POST.get("section", "specs")

        if name:
            attribute.name = name
            attribute.section = section
            attribute.save()
            return redirect("adminpanel:categories")

    return render(request, "adminpanel/edit_attribute.html", {
        "attribute": attribute
    })
# delete attributes safely with confirmation.
@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def delete_attribute(request, id):

    if request.method == "POST":
        Attribute.objects.filter(id=id).delete()
        messages.success(request, "Attribute deleted")
        return redirect('adminpanel:categories')

    attribute = get_object_or_404(Attribute, id=id)
    return render(request, "adminpanel/delete_attribute.html", {
        "attribute": attribute
    })


# ================= BUNDLES =================

@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def admin_bundles(request):
    bundles = Bundle.objects.prefetch_related("products").order_by("-created_at")
    all_products = Product.objects.filter(status="approved", is_active=True).prefetch_related("variants").order_by("name")
    return render(request, "adminpanel/bundles.html", {
        "bundles": bundles,
        "all_products": all_products,
    })


@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def create_bundle(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        main_product_id = request.POST.get("main_product", "").strip()
        bundle_price = request.POST.get("bundle_price", "").strip()
        is_active = request.POST.get("is_active") == "on"
        product_ids = request.POST.getlist("products")

        if main_product_id:
            product_ids = [main_product_id] + [pid for pid in product_ids if pid != main_product_id]

        product_ids = list(dict.fromkeys(pid for pid in product_ids if pid))

        discounted_prices = {}
        missing_discounted = False
        invalid_discounted = False
        for pid in product_ids:
            raw_val = request.POST.get(f"discounted_price_{pid}", "").strip()
            if not raw_val:
                missing_discounted = True
                break
            try:
                discounted_val = Decimal(raw_val)
                if discounted_val <= 0:
                    invalid_discounted = True
                    break
                discounted_prices[pid] = discounted_val
            except (InvalidOperation, TypeError):
                invalid_discounted = True
                break

        if name and bundle_price and main_product_id and not missing_discounted and not invalid_discounted:
            bundle = Bundle.objects.create(
                name=name,
                bundle_price=bundle_price,
                is_active=is_active,
            )
            bundle.products.set(product_ids)
            for pid in product_ids:
                BundleProduct.objects.filter(bundle=bundle, product_id=pid).update(
                    discounted_price=discounted_prices.get(pid)
                )
            messages.success(request, f"Bundle '{name}' created successfully.")
        else:
            if missing_discounted:
                messages.error(request, "Add discounted price for each selected product.")
            elif invalid_discounted:
                messages.error(request, "Discounted price must be a valid value greater than 0.")
            else:
                messages.error(request, "Bundle name, main product and calculated bundle price are required.")
    return redirect("adminpanel:admin_bundles")


@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def edit_bundle(request, bundle_id):
    bundle = get_object_or_404(Bundle, id=bundle_id)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        bundle_price = request.POST.get("bundle_price", "").strip()
        is_active = request.POST.get("is_active") == "on"
        product_ids = request.POST.getlist("products")
        discounted_prices = {}

        for pid in product_ids:
            raw_val = request.POST.get(f"discounted_price_{pid}", "").strip()
            if not raw_val:
                continue
            try:
                discounted_val = Decimal(raw_val)
            except (InvalidOperation, TypeError):
                continue
            if discounted_val > 0:
                discounted_prices[pid] = discounted_val

        if name and bundle_price:
            bundle.name = name
            bundle.bundle_price = bundle_price
            bundle.is_active = is_active
            bundle.save()
            bundle.products.set(product_ids)
            for pid in product_ids:
                if pid in discounted_prices:
                    BundleProduct.objects.filter(bundle=bundle, product_id=pid).update(
                        discounted_price=discounted_prices[pid]
                    )
            messages.success(request, f"Bundle '{name}' updated.")
        return redirect("adminpanel:admin_bundles")

    all_products = Product.objects.filter(status="approved", is_active=True).order_by("name")
    selected_ids = list(bundle.products.values_list("id", flat=True))
    return render(request, "adminpanel/bundle_edit.html", {
        "bundle": bundle,
        "all_products": all_products,
        "selected_ids": selected_ids,
    })


@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def delete_bundle(request, bundle_id):
    bundle = get_object_or_404(Bundle, id=bundle_id)
    bundle.delete()
    messages.success(request, "Bundle deleted.")
    return redirect("adminpanel:admin_bundles")


# ================= REVIEWS =================

@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def admin_reviews(request):
    status_filter = request.GET.get("status", "pending")

    if status_filter == "approved":
        reviews_qs = Review.objects.filter(approved=True)
    elif status_filter == "rejected":
        reviews_qs = Review.objects.filter(approved=False).exclude(
            # exclude newly-submitted ones that were never touched
            id__in=Review.objects.filter(approved=False)
        )
        # simpler: just show all non-approved
        reviews_qs = Review.objects.filter(approved=False)
    else:  # pending (default)
        reviews_qs = Review.objects.filter(approved=False)

    reviews_qs = reviews_qs.select_related("product", "user").order_by("-created")

    total_pending  = Review.objects.filter(approved=False).count()
    total_approved = Review.objects.filter(approved=True).count()

    return render(request, "adminpanel/reviews.html", {
        "reviews":        reviews_qs,
        "status_filter":  status_filter,
        "total_pending":  total_pending,
        "total_approved": total_approved,
    })


@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def approve_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.approved = True
    review.save()
    messages.success(request, f"Review by '{review.user.username}' approved and is now visible to customers.")
    return redirect("adminpanel:admin_reviews")


@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def reject_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.approved = False
    review.save()
    messages.success(request, f"Review by '{review.user.username}' has been hidden.")
    return redirect("adminpanel:admin_reviews")


@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.delete()
    messages.success(request, "Review deleted.")
    return redirect("adminpanel:admin_reviews")


# ================= SALES =================

@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def admin_sales(request):
    sales = Sale.objects.all().order_by("-created_at")
    return render(request, "adminpanel/sales.html", {"sales": sales})


@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def create_sale(request):
    if request.method == "POST":
        title          = request.POST.get("title", "").strip()
        description    = request.POST.get("description", "").strip()
        banner_text    = request.POST.get("banner_text", "").strip()
        start_datetime = request.POST.get("start_datetime", "")
        end_datetime   = request.POST.get("end_datetime", "")
        is_active      = request.POST.get("is_active") == "on"

        if title and start_datetime and end_datetime:
            sale = Sale.objects.create(
                title=title,
                description=description,
                banner_text=banner_text,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                is_active=is_active,
                created_by=request.user,
            )
            # Send notifications to all vendors
            vendor_group = Group.objects.filter(name="vendor").first()
            if vendor_group:
                for vendor_user in vendor_group.user_set.all():
                    VendorSaleNotification.objects.get_or_create(
                        sale=sale, vendor=vendor_user
                    )
            messages.success(request, f"Sale '{sale.title}' created and {vendor_group.user_set.count() if vendor_group else 0} vendors notified.")
            return redirect("adminpanel:admin_sales")
        else:
            messages.error(request, "Please fill in all required fields.")

    return render(request, "adminpanel/sale_form.html", {"action": "Create"})


@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def edit_sale(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)
    if request.method == "POST":
        sale.title          = request.POST.get("title", sale.title).strip()
        sale.description    = request.POST.get("description", "").strip()
        sale.banner_text    = request.POST.get("banner_text", "").strip()
        sale.start_datetime = request.POST.get("start_datetime", sale.start_datetime)
        sale.end_datetime   = request.POST.get("end_datetime", sale.end_datetime)
        sale.is_active      = request.POST.get("is_active") == "on"
        sale.save()
        messages.success(request, "Sale updated.")
        return redirect("adminpanel:admin_sales")
    return render(request, "adminpanel/sale_form.html", {"action": "Edit", "sale": sale})


@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def delete_sale(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)
    sale.delete()
    messages.success(request, "Sale deleted.")
    return redirect("adminpanel:admin_sales")


@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def admin_sale_ads(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)
    status_filter = request.GET.get("status", "pending")
    if status_filter == "approved":
        ads = SaleAdvertisement.objects.filter(sale=sale, is_approved=True)
    else:
        ads = SaleAdvertisement.objects.filter(sale=sale, is_approved=False)
    ads = ads.select_related("vendor", "product").order_by("-created_at")
    return render(request, "adminpanel/sale_ads.html", {
        "sale": sale,
        "ads": ads,
        "status_filter": status_filter,
        "pending_count": SaleAdvertisement.objects.filter(sale=sale, is_approved=False).count(),
        "approved_count": SaleAdvertisement.objects.filter(sale=sale, is_approved=True).count(),
    })


@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def approve_sale_ad(request, ad_id):
    ad = get_object_or_404(SaleAdvertisement, id=ad_id)
    ad.is_approved = True
    ad.save()
    messages.success(request, f"Ad by '{ad.vendor.username}' approved.")
    return redirect("adminpanel:admin_sale_ads", sale_id=ad.sale_id)


@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def reject_sale_ad(request, ad_id):
    ad = get_object_or_404(SaleAdvertisement, id=ad_id)
    ad.is_approved = False
    ad.save()
    messages.success(request, f"Ad by '{ad.vendor.username}' rejected.")
    return redirect("adminpanel:admin_sale_ads", sale_id=ad.sale_id)


@login_required(login_url="/adminpanel/")
@user_passes_test(is_admin)
def end_sale(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)
    sale.end_datetime = timezone.now()
    sale.is_active = False
    sale.save()
    messages.success(request, f"Sale '{sale.title}' has been ended.")
    return redirect("adminpanel:admin_sales")