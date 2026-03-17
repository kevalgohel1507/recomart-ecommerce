from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from products.models import ProductVariant, Bundle
from orders.models import Order
from recommender.models import UserInteraction


SHIPPING = Decimal('40')
PLATFORM_FEE_PCT = Decimal('0.05')   # 5% of subtotal
GST_ON_PLATFORM_PCT = Decimal('0.18')  # 18% GST on platform fee


def _get_cart_price_overrides(request):
    raw = request.session.get("cart_price_overrides", {})
    return raw if isinstance(raw, dict) else {}


def _effective_unit_price(variant, price_overrides):
    raw_price = price_overrides.get(str(variant.id))
    if raw_price is None:
        return variant.price
    try:
        parsed = Decimal(str(raw_price))
        return parsed if parsed > 0 else variant.price
    except Exception:
        return variant.price


# ================= ADD TO CART =================

def add_cart(request, id):

    variant = get_object_or_404(ProductVariant, id=id)

    if variant.stock <= 0:
        return redirect("cart")

    cart = request.session.get("cart", {})
    vid = str(variant.id)

    if vid in cart:
        if cart[vid] < variant.stock:
            cart[vid] += 1
    else:
        cart[vid] = 1

    request.session["cart"] = cart
    request.session.modified = True

    if request.user.is_authenticated:
        UserInteraction.objects.create(
            user=request.user,
            product_id=variant.product.id,
            action_type="cart",
            score=2,
        )

    return redirect("cart")


# ================= VIEW CART =================

@login_required
def cart_view(request):

    cart = request.session.get("cart", {})
    price_overrides = _get_cart_price_overrides(request)
    items = []
    subtotal = 0

    for vid, qty in cart.items():

        variant = get_object_or_404(
            ProductVariant.objects.select_related("product"),
            id=vid
        )

        qty = min(qty, variant.stock)
        cart[vid] = qty

        unit_price = _effective_unit_price(variant, price_overrides)
        line_total = unit_price * qty
        subtotal += line_total

        # savings: difference between MRP and selling price
        mrp = variant.mrp if (variant.mrp and variant.mrp > unit_price) else None
        unit_saving = (mrp - unit_price) if mrp else 0
        line_saving = unit_saving * qty
        discount_pct = int((unit_saving / mrp) * 100) if mrp else 0

        items.append({
            "variant": variant,
            "product": variant.product,
            "qty": qty,
            "price": unit_price,
            "mrp": mrp,
            "unit_saving": unit_saving,
            "line_saving": line_saving,
            "discount_pct": discount_pct,
            "subtotal": line_total,
            "image": variant.images.first(),
        })

    request.session["cart"] = cart

    # Drop stale overrides for items no longer present in cart.
    valid_keys = set(str(k) for k in cart.keys())
    stale_keys = [k for k in price_overrides.keys() if k not in valid_keys]
    if stale_keys:
        for k in stale_keys:
            price_overrides.pop(k, None)
        request.session["cart_price_overrides"] = price_overrides
        request.session.modified = True

    platform_fee = round(subtotal * PLATFORM_FEE_PCT, 2)
    gst_on_platform = round(platform_fee * GST_ON_PLATFORM_PCT, 2)
    total = subtotal + platform_fee + gst_on_platform + SHIPPING
    savings = sum(item["line_saving"] for item in items)

    return render(request, "cart/cart.html", {
        "items": items,
        "subtotal": subtotal,
        "platform_fee": platform_fee,
        "gst_on_platform": gst_on_platform,
        "shipping": SHIPPING,
        "total": total,
        "savings": savings,
    })


# ================= UPDATE CART =================

@login_required
def update_cart(request):

    cart = request.session.get("cart", {})
    price_overrides = _get_cart_price_overrides(request)
    vid = request.POST.get("variant_id")
    action = request.POST.get("action")

    if vid not in cart:
        return redirect("cart")

    variant = get_object_or_404(ProductVariant, id=vid)

    if action == "increase" and cart[vid] < variant.stock:
        cart[vid] += 1

    elif action == "decrease":
        cart[vid] -= 1
        if cart[vid] <= 0:
            cart.pop(vid)
            price_overrides.pop(vid, None)

    request.session["cart"] = cart
    request.session["cart_price_overrides"] = price_overrides
    request.session.modified = True

    return redirect("cart")


# ================= REMOVE ITEM =================

@login_required
def remove_cart(request, id):

    cart = request.session.get("cart", {})
    price_overrides = _get_cart_price_overrides(request)
    vid = str(id)

    if vid in cart:
        cart.pop(vid)
    price_overrides.pop(vid, None)

    request.session["cart"] = cart
    request.session["cart_price_overrides"] = price_overrides
    request.session.modified = True

    return redirect("cart")


# ================= ADDRESS STEP =================

@login_required
def checkout_address(request):

    if request.method == "POST":

        address = {
            "full_name": request.POST.get("full_name", "").strip(),
            "address": request.POST.get("address", "").strip(),
            "city": request.POST.get("city", "").strip(),
            "state": request.POST.get("state", "").strip(),
            "pincode": request.POST.get("pincode", "").strip(),
            "phone": request.POST.get("phone", "").strip(),
        }

        if not all(address.values()):
            messages.error(request, "Fill all address fields.")
            return redirect("checkout_address")

        request.session["shipping_address"] = address
        request.session.modified = True

        return redirect("checkout")

    return render(request, "cart/checkout_address.html")


# ================= CHECKOUT REVIEW =================

@login_required
def checkout(request):

    cart = request.session.get("cart", {})
    price_overrides = _get_cart_price_overrides(request)
    address = request.session.get("shipping_address")

    if not address:
        return redirect("checkout_address")

    items = []
    subtotal = 0

    for vid, qty in cart.items():

        variant = get_object_or_404(ProductVariant, id=vid)

        unit_price = _effective_unit_price(variant, price_overrides)
        line_total = unit_price * qty
        subtotal += line_total

        items.append({
            "variant": variant,
            "product": variant.product,
            "qty": qty,
            "price": unit_price,
            "subtotal": line_total,
        })

    platform_fee = round(subtotal * PLATFORM_FEE_PCT, 2)
    gst_on_platform = round(platform_fee * GST_ON_PLATFORM_PCT, 2)
    grand_total = subtotal + platform_fee + gst_on_platform + SHIPPING

    # -------- PLACE ORDER --------
    if request.method == "POST":

        payment = request.POST.get("payment", "COD")

        full_address = (
            f"{address['address']}, {address['city']}, "
            f"{address['state']} - {address['pincode']} "
            f"| Ph: {address['phone']}"
        )

        order_ids = []
        for item in items:

            variant = item["variant"]
            qty = item["qty"]
            line_total = float(item["subtotal"])
            line_platform_fee = round(line_total * 0.12, 2)
            line_platform_fee_gst = round(line_platform_fee * 0.18, 2)
            line_vendor_profit = round(line_total - line_platform_fee - line_platform_fee_gst, 2)

            if variant.stock < qty:
                continue

            variant.stock -= qty
            variant.save()

            order = Order.objects.create(
                customer=request.user,
                vendor=variant.product.vendor,
                product=variant.product,
                variant=variant,
                quantity=qty,
                total=line_total,
                platform_fee=line_platform_fee,
                platform_fee_gst=line_platform_fee_gst,
                vendor_profit=line_vendor_profit,
                address=full_address,
                pincode=address["pincode"],
                payment_method=payment,
            )
            order_ids.append(order.id)

            UserInteraction.objects.create(
                user=request.user,
                product_id=variant.product.id,
                action_type="purchase",
                score=3,
            )

        request.session["cart"] = {}
        request.session["cart_price_overrides"] = {}
        request.session.pop("shipping_address", None)

        # Store bill data so the success page can link to it
        request.session["last_bill"] = {
            "order_ids": order_ids,
            "subtotal": float(subtotal),
            "platform_fee": float(platform_fee),
            "gst_on_platform": float(gst_on_platform),
            "shipping": float(SHIPPING),
            "total": float(grand_total),
            "address": full_address,
            "payment": payment,
        }
        request.session.modified = True

        return redirect("order_success")

    return render(request, "cart/checkout.html", {
        "items": items,
        "subtotal": subtotal,
        "platform_fee": platform_fee,
        "gst_on_platform": gst_on_platform,
        "shipping": SHIPPING,
        "total": grand_total,
        "address": address,
    })


# ================= SUCCESS =================

@login_required
def order_success(request):
    return render(request, "cart/success.html")


# ================= ADD BUNDLE TO CART =================

def add_bundle_to_cart(request):
    if request.method == "POST":
        bundle_id = request.POST.get("bundle_id")
        variant_ids = request.POST.getlist("variants")
        cart = request.session.get("cart", {})
        price_overrides = _get_cart_price_overrides(request)

        bundle = None
        discount_map = {}
        allowed_product_ids = set()
        if bundle_id:
            try:
                bundle = Bundle.objects.prefetch_related("bundle_items", "products").get(
                    id=int(bundle_id),
                    is_active=True,
                )
                for bp in bundle.bundle_items.all():
                    if bp.discounted_price is not None and bp.discounted_price > 0:
                        discount_map[bp.product_id] = bp.discounted_price
                allowed_product_ids = set(bundle.products.values_list("id", flat=True))
            except (Bundle.DoesNotExist, ValueError, TypeError):
                bundle = None

        for vid in variant_ids:
            try:
                variant = ProductVariant.objects.get(id=int(vid))
                if variant.stock > 0:
                    vid_str = str(variant.id)
                    if vid_str in cart:
                        if cart[vid_str] < variant.stock:
                            cart[vid_str] += 1
                    else:
                        cart[vid_str] = 1

                    # Preserve per-variant bundle price so cart and checkout totals stay consistent.
                    if bundle and variant.product_id in allowed_product_ids:
                        discounted_price = discount_map.get(variant.product_id)
                        if discounted_price is not None and discounted_price > 0:
                            price_overrides[vid_str] = str(discounted_price)

                    if request.user.is_authenticated:
                        UserInteraction.objects.create(
                            user=request.user,
                            product_id=variant.product.id,
                            action_type="cart",
                            score=2,
                        )
            except (ProductVariant.DoesNotExist, ValueError):
                continue
        request.session["cart"] = cart
        request.session["cart_price_overrides"] = price_overrides
        request.session.modified = True
    return redirect("cart")