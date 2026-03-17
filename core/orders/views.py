import hmac
import hashlib
from decimal import Decimal

from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.conf import settings

import razorpay

from .models import Order


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


# ================= MY ORDERS =================

@login_required
def my_orders(request):
    from collections import OrderedDict

    SHIPPING        = 40.0
    PLATFORM_FEE_PCT = 0.05
    GST_PCT         = 0.18

    all_orders = (
        Order.objects
        .filter(customer=request.user)
        .select_related("product", "variant", "vendor")
        .order_by("-created")
    )

    # Group by razorpay_order_id so multi-vendor checkouts appear as one purchase.
    # COD / old orders without an rzp ID get their own solo group.
    group_map = OrderedDict()
    for order in all_orders:
        key = order.razorpay_order_id if order.razorpay_order_id else f"solo_{order.id}"
        if key not in group_map:
            group_map[key] = {
                "key":            key,
                "orders":         [],
                "date":           order.created,
                "payment_id":     order.razorpay_payment_id,
                "payment_status": order.payment_status,
            }
        group_map[key]["orders"].append(order)

    order_groups = []
    for grp in group_map.values():
        orders   = grp["orders"]
        subtotal = sum(o.total for o in orders)
        platform_fee = round(subtotal * PLATFORM_FEE_PCT, 2)
        gst          = round(platform_fee * GST_PCT, 2)
        final_total  = round(subtotal + platform_fee + gst + SHIPPING, 2)

        order_groups.append({
            "key":            grp["key"],
            "orders":         orders,
            "date":           grp["date"],
            "payment_id":     grp["payment_id"],
            "payment_status": grp["payment_status"],
            "subtotal":       round(subtotal, 2),
            "platform_fee":   platform_fee,
            "gst":            gst,
            "final_total":    final_total,
            "multi_vendor":   len({o.vendor_id for o in orders}) > 1,
        })

    return render(request, "orders/my_orders.html", {"order_groups": order_groups})


@login_required
def cancel_order(request):

    if request.method=="POST":

        order_id = request.POST['order_id']
        reason = request.POST['reason']
        note = request.POST['note']

        order = Order.objects.get(id=order_id)

        order.status = "Cancelled"
        order.cancel_reason = reason
        order.cancel_note = note
        order.save()

    return redirect('/orders/my-orders/')


@login_required
def order_bill(request):
    bill = request.session.get("last_bill")
    if not bill:
        return redirect("my_orders")

    orders = Order.objects.filter(
        id__in=bill["order_ids"],
        customer=request.user,
    ).select_related("product", "variant")

    context = {
        "orders": orders,
        "subtotal": bill["subtotal"],
        "platform_fee": bill["platform_fee"],
        "gst_on_platform": bill["gst_on_platform"],
        "shipping": bill["shipping"],
        "total": bill["total"],
        "address": bill["address"],
        "payment": bill["payment"],
        "customer": request.user,
    }

    html_string = render_to_string("orders/bill_pdf.html", context, request=request)

    from io import BytesIO
    from xhtml2pdf import pisa

    buffer = BytesIO()
    pisa.CreatePDF(html_string, dest=buffer)
    pdf_file = buffer.getvalue()

    response = HttpResponse(pdf_file, content_type="application/pdf")
    invoice_num = f"RM-{orders[0].id:06d}" if orders else "RM-000000"
    response["Content-Disposition"] = f'inline; filename="Recomart-Invoice-{invoice_num}.pdf"'
    return response


# ================= RAZORPAY: CREATE ORDER =================

@login_required
@require_POST
def create_razorpay_order(request):
    """Dynamically compute cart total and create a Razorpay order. Returns JSON."""
    from cart.views import SHIPPING, PLATFORM_FEE_PCT, GST_ON_PLATFORM_PCT
    from products.models import ProductVariant

    cart = request.session.get("cart", {})
    price_overrides = _get_cart_price_overrides(request)
    if not cart:
        return JsonResponse({"error": "Cart is empty"}, status=400)

    subtotal = Decimal("0")
    for vid, qty in cart.items():
        try:
            variant = ProductVariant.objects.get(id=vid)
            unit_price = _effective_unit_price(variant, price_overrides)
            subtotal += unit_price * qty
        except ProductVariant.DoesNotExist:
            continue

    platform_fee = round(subtotal * PLATFORM_FEE_PCT, 2)
    gst_on_platform = round(platform_fee * GST_ON_PLATFORM_PCT, 2)
    grand_total = subtotal + platform_fee + gst_on_platform + SHIPPING

    amount_paise = int(grand_total * 100)

    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        rp_order = client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "payment_capture": 1,
            "receipt": f"user_{request.user.id}",
            "notes": {"user_id": str(request.user.id)},
        })
    except Exception as e:
        return JsonResponse({"error": f"Razorpay API error: {str(e)}"}, status=500)

    # Store in session for cross-verification on payment success
    request.session["rzp_order_id"] = rp_order["id"]
    request.session.modified = True

    return JsonResponse({
        "razorpay_order_id": rp_order["id"],
        "amount": amount_paise,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
    })


# ================= RAZORPAY: PAYMENT SUCCESS =================

@login_required
@require_POST
def razorpay_payment_success(request):
    """Verify Razorpay signature, place orders, and redirect to success page."""
    razorpay_order_id   = request.POST.get("razorpay_order_id", "")
    razorpay_payment_id = request.POST.get("razorpay_payment_id", "")
    razorpay_signature  = request.POST.get("razorpay_signature", "")
    payment_method      = request.POST.get("payment_method", "RAZORPAY")

    # Cross-check: order ID must match what was created in this session
    session_order_id = request.session.get("rzp_order_id", "")
    if not session_order_id or session_order_id != razorpay_order_id:
        django_messages.error(request, "Invalid payment session. Please try again.")
        return redirect("checkout")

    # Verify Razorpay HMAC-SHA256 signature
    key_secret = settings.RAZORPAY_KEY_SECRET.encode()
    message = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected_signature = hmac.new(key_secret, message, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_signature, razorpay_signature):
        django_messages.error(request, "Payment verification failed. Please contact support.")
        return redirect("checkout")

    # Signature verified — place the orders
    from cart.views import SHIPPING, PLATFORM_FEE_PCT, GST_ON_PLATFORM_PCT
    from products.models import ProductVariant
    from recommender.models import UserInteraction

    cart    = request.session.get("cart", {})
    price_overrides = _get_cart_price_overrides(request)
    address = request.session.get("shipping_address")

    if not cart or not address:
        return redirect("cart")

    items    = []
    subtotal = Decimal("0")
    for vid, qty in cart.items():
        try:
            variant    = ProductVariant.objects.get(id=vid)
            unit_price = _effective_unit_price(variant, price_overrides)
            line_total = unit_price * qty
            subtotal  += line_total
            items.append({"variant": variant, "qty": qty, "subtotal": line_total})
        except ProductVariant.DoesNotExist:
            continue

    platform_fee    = round(subtotal * PLATFORM_FEE_PCT, 2)
    gst_on_platform = round(platform_fee * GST_ON_PLATFORM_PCT, 2)
    grand_total     = subtotal + platform_fee + gst_on_platform + SHIPPING

    full_address = (
        f"{address['address']}, {address['city']}, "
        f"{address['state']} - {address['pincode']} "
        f"| Ph: {address['phone']}"
    )

    order_ids = []
    for item in items:
        variant = item["variant"]
        qty     = item["qty"]
        line_total = float(item["subtotal"])
        line_platform_fee = round(line_total * 0.12, 2)
        line_platform_fee_gst = round(line_platform_fee * 0.18, 2)
        line_vendor_profit = round(line_total - line_platform_fee - line_platform_fee_gst, 2)
        if variant.stock < qty:
            continue
        variant.stock -= qty
        variant.save()

        order = Order.objects.create(
            customer            = request.user,
            vendor              = variant.product.vendor,
            product             = variant.product,
            variant             = variant,
            quantity            = qty,
            total               = line_total,
            platform_fee        = line_platform_fee,
            platform_fee_gst    = line_platform_fee_gst,
            vendor_profit       = line_vendor_profit,
            address             = full_address,
            pincode             = address["pincode"],
            payment_method      = payment_method,
            razorpay_order_id   = razorpay_order_id,
            razorpay_payment_id = razorpay_payment_id,
            payment_status      = "Paid",
        )
        order_ids.append(order.id)

        UserInteraction.objects.create(
            user        = request.user,
            product_id  = variant.product.id,
            action_type = "purchase",
            score       = 3,
        )

    # Clear cart, address, and Razorpay order from session
    request.session["cart"] = {}
    request.session["cart_price_overrides"] = {}
    request.session.pop("shipping_address", None)
    request.session.pop("rzp_order_id", None)

    request.session["last_bill"] = {
        "order_ids":        order_ids,
        "subtotal":         float(subtotal),
        "platform_fee":     float(platform_fee),
        "gst_on_platform":  float(gst_on_platform),
        "shipping":         float(SHIPPING),
        "total":            float(grand_total),
        "address":          full_address,
        "payment":          payment_method,
    }
    request.session.modified = True

    return redirect("order_success")