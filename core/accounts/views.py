from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from products.models import Product, Category
from orders.models import Order
from django.core.paginator import Paginator
from products.models import Product
from .models import UserProfile, GuestLocation

import json
import random


# ================= REGISTER =================

def register(request):

    if request.method == "POST":

        username = request.POST.get("username")
        email    = request.POST.get("email")
        phone    = request.POST.get("phone")
        password = request.POST.get("password")
        confirm  = request.POST.get("confirm")
        role     = request.POST.get("role")

        if not all([username, email, phone, password, confirm, role]):
            messages.error(request, "All fields are required.")
            return redirect("register")

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("register")

        # ── OTP verification check ──
        if request.session.get("email_verified_for") != email:
            messages.error(request, "Email OTP not verified. Please verify your email first.")
            return redirect("register")

        if request.session.get("phone_verified_for") != phone:
            messages.error(request, "Phone OTP not verified. Please verify your phone first.")
            return redirect("register")

        # ── Create user ──
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        UserProfile.objects.create(
            user=user,
            phone=phone,
            role=role,
            email_verified=True,   # verified via OTP
            phone_verified=True,   # verified via OTP
        )

        # Assign group
        group, _ = Group.objects.get_or_create(name=role)
        user.groups.clear()
        user.groups.add(group)

        # Clear OTP session data
        for key in ("email_otp", "email_verified_for", "phone_otp", "phone_verified_for"):
            request.session.pop(key, None)

        messages.success(request, "Account created successfully! Please login.")
        return redirect("login")

    return render(request, "accounts/register.html")


# ================= LOGIN =================

def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)

            # SUPERUSER or ADMIN GROUP → custom admin panel
            if user.is_superuser or user.groups.filter(name="admin").exists():
                return redirect("adminpanel:admin_dashboard")

            # VENDOR
            if user.groups.filter(name="vendor").exists():
                return redirect("vendor_dashboard")

            # CUSTOMER
            return redirect("home")

        messages.error(request, "Invalid username or password")

    return render(request, "accounts/login.html")


# ================= LOGOUT =================

def logout_view(request):
    logout(request)
    return redirect("home")


# ================= PROFILE =================

@login_required
def profile(request):
    return render(request, "accounts/profile.html")


# ================= ADMIN DASHBOARD =================

@login_required
def admin_dashboard(request):

    # Admin permission check
    if not request.user.groups.filter(name="admin").exists():
        return HttpResponseForbidden("Not allowed")

    context = {

        # ===== MAIN STATS =====
        "products": Product.objects.count(),
        "orders": Order.objects.count(),
        "categories": Category.objects.count(),
        "users": User.objects.count(),

        # ===== RECENT DATA =====
        "recent_orders": Order.objects.select_related("user").order_by("-id")[:5],
        "recent_users": User.objects.order_by("-date_joined")[:5],
        "low_stock_products": Product.objects.filter(stock__lt=5).order_by("stock")[:5],

    }

    return render(request, "adminpanel/dashboard.html", context)
# ================= EMAIL OTP – SEND =================

@csrf_exempt
def send_email_otp(request):
    try:
        data  = json.loads(request.body)
        email = data.get("email", "").strip()
    except Exception:
        return JsonResponse({"status": "error", "msg": "Invalid request."}, status=400)

    if not email:
        return JsonResponse({"status": "error", "msg": "Email is required."}, status=400)

    otp = str(random.randint(100000, 999999))
    request.session["email_otp"]          = otp
    request.session["email_otp_for"]      = email   # track which email the OTP belongs to
    request.session.pop("email_verified_for", None)  # reset any previous verified state

    try:
        send_mail(
            subject="Your E-Commerce Email Verification OTP",
            message=(
                f"Hello,\n\n"
                f"Your email verification OTP is: {otp}\n\n"
                f"This OTP is valid for 10 minutes. Do not share it with anyone.\n\n"
                f"– E-Commerce Team"
            ),
            from_email=None,   # uses DEFAULT_FROM_EMAIL from settings
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as e:
        return JsonResponse({"status": "error", "msg": f"Failed to send email: {e}"}, status=500)

    return JsonResponse({"status": "success", "msg": "OTP sent to your email."})


# ================= EMAIL OTP – VERIFY =================

@csrf_exempt
def verify_email_otp(request):
    try:
        data = json.loads(request.body)
        otp  = str(data.get("otp", "")).strip()
    except Exception:
        return JsonResponse({"status": "error", "msg": "Invalid request."}, status=400)

    saved_otp = request.session.get("email_otp")
    email_for = request.session.get("email_otp_for")

    if not saved_otp:
        return JsonResponse({"status": "error", "msg": "No OTP requested. Please send OTP first."})

    if otp != saved_otp:
        return JsonResponse({"status": "error", "msg": "Incorrect OTP. Please try again."})

    # Mark email as verified in session so register view can trust it
    request.session["email_verified_for"] = email_for
    request.session.pop("email_otp", None)
    request.session.pop("email_otp_for", None)

    return JsonResponse({"status": "success", "msg": "Email verified successfully!"})


# ================= PHONE OTP – SEND =================

@csrf_exempt
def send_phone_otp(request):
    try:
        data  = json.loads(request.body)
        phone = data.get("phone", "").strip()
    except Exception:
        return JsonResponse({"status": "error", "msg": "Invalid request."}, status=400)

    if not phone:
        return JsonResponse({"status": "error", "msg": "Phone number is required."}, status=400)

    otp = str(random.randint(100000, 999999))
    request.session["phone_otp"]     = otp
    request.session["phone_otp_for"] = phone
    request.session.pop("phone_verified_for", None)

    # ⚠️ SMS gateway integration: replace the print below with your SMS API call
    print(f"[SMS] Phone: {phone}  OTP: {otp}")

    return JsonResponse({"status": "success", "msg": "OTP sent to your phone."})


# ================= PHONE OTP – VERIFY =================

@csrf_exempt
def verify_phone_otp(request):
    try:
        data = json.loads(request.body)
        otp  = str(data.get("otp", "")).strip()
    except Exception:
        return JsonResponse({"status": "error", "msg": "Invalid request."}, status=400)

    saved_otp = request.session.get("phone_otp")
    phone_for = request.session.get("phone_otp_for")

    if not saved_otp:
        return JsonResponse({"status": "error", "msg": "No OTP requested. Please send OTP first."})

    if otp != saved_otp:
        return JsonResponse({"status": "error", "msg": "Incorrect OTP. Please try again."})

    request.session["phone_verified_for"] = phone_for
    request.session.pop("phone_otp", None)
    request.session.pop("phone_otp_for", None)

    return JsonResponse({"status": "success", "msg": "Phone verified successfully!"})


# ================= GUEST LOCATION =================

@csrf_exempt
def save_guest_location(request):
    """Receives location data from an unauthenticated visitor and stores it in GuestLocation.
    lat/lng are optional – manual city-only entries are accepted too.  POST-only, returns JSON."""

    if request.method != "POST":
        return JsonResponse({"status": "error", "msg": "POST required"}, status=405)

    # Reject authenticated users – they have a full profile
    if request.user.is_authenticated:
        return JsonResponse({"status": "skip", "msg": "user is logged in"})

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"status": "error", "msg": "Invalid JSON"}, status=400)

    # At least a city must be present when coords are absent
    lat    = data.get("latitude")
    lng    = data.get("longitude")
    city   = data.get("city", "").strip()
    source = data.get("source", "gps")

    if source not in ("gps", "ip", "manual"):
        source = "manual"

    if lat is None and lng is None and not city:
        return JsonResponse({"status": "error", "msg": "At least a city or coordinates are required."}, status=400)

    # Get client IP safely (supports reverse-proxy X-Forwarded-For)
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")

    # Ensure session exists so we can store a key
    if not request.session.session_key:
        request.session.create()

    GuestLocation.objects.create(
        session_key = request.session.session_key,
        ip_address  = ip,
        latitude    = lat,
        longitude   = lng,
        city        = city,
        state       = data.get("state", "").strip(),
        country     = data.get("country", "").strip(),
        source      = source,
    )

    # Mark in session so the popup doesn't reappear this visit
    request.session["location_captured"] = True

    return JsonResponse({"status": "success", "msg": "Location saved"})



# def admin_products(request):

#     product_list = Product.objects.all().order_by("-id")  # Fetch all products

#     paginator = Paginator(product_list, 12)  # 12 per page
#     page_number = request.GET.get("page")
#     products = paginator.get_page(page_number)

#     context = {
#         "products": products
#     }

#     return render(request, "adminpanel/products.html", context)