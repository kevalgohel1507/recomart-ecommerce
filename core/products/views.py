from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Prefetch, Count, Min
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.cache import cache
import json
import uuid
import re
import difflib
from datetime import timedelta

from .models import (
    Product, Category, Review, ProductVariant, ReviewImage, Sale, SaleAdvertisement,
    VariantAttributeValue, VariantImage, Bundle, BundleProduct, SearchQuery,
)
from recommender.models import UserRecommendation, UserInteraction

# =====================================================
# NLP SEARCH HELPERS
# =====================================================

_STOP_WORDS = {
    'a', 'an', 'the', 'is', 'in', 'on', 'at', 'to', 'for', 'of',
    'and', 'or', 'with', 'from', 'by', 'about', 'it', 'its',
    'me', 'my', 'i', 'we', 'you', 'he', 'she', 'they',
}

_SYNONYMS = {
    'phone':     ['mobile', 'smartphone', 'iphone', 'android'],
    'laptop':    ['notebook', 'computer', 'macbook'],
    'tv':        ['television', 'monitor'],
    'headphone': ['earphone', 'earbuds', 'headset', 'buds'],
    'shoe':      ['sneaker', 'boot', 'footwear', 'sandal'],
    'shirt':     ['tshirt', 't-shirt', 'top', 'blouse'],
    'pants':     ['jeans', 'trouser', 'chino', 'shorts'],
    'bag':       ['backpack', 'purse', 'handbag', 'satchel'],
    'watch':     ['smartwatch', 'timepiece'],
}
# Reverse map: 'iphone' -> 'phone', 'earbuds' -> 'headphone'
_REVERSE_SYNONYMS = {alias: canon for canon, aliases in _SYNONYMS.items() for alias in aliases}


def _tokenize(text):
    """Lowercase, strip punctuation, remove stop-words; return token list."""
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    return [t for t in text.split() if t not in _STOP_WORDS and len(t) > 1]


def _expand_tokens(tokens):
    """Add synonym variants so 'earbuds' also searches 'headphone'."""
    extra = []
    for t in tokens:
        canon = _REVERSE_SYNONYMS.get(t)
        if canon:
            extra.append(canon)
        if t in _SYNONYMS:
            extra.extend(_SYNONYMS[t])
    return tokens + extra


def _nlp_product_score(product, tokens):
    """Score a product against query tokens. Higher = better match."""
    score = 0.0
    name_l = product.name.lower()
    brand_l = (product.brand or '').lower()
    desc_l  = (product.short_description or '').lower()

    for token in tokens:
        # Exact substring match
        if token in name_l:
            score += 3.0
        elif name_l.startswith(token):
            score += 2.5
        else:
            # Fuzzy: compare token against every word in name
            name_words = name_l.split()
            best = max(
                (difflib.SequenceMatcher(None, token, w).ratio() for w in name_words),
                default=0,
            )
            if best >= 0.75:
                score += best * 2.0

        if token in brand_l:
            score += 2.0
        elif brand_l and difflib.SequenceMatcher(None, token, brand_l).ratio() >= 0.70:
            score += 1.0

        if token in desc_l:
            score += 0.5

    return score


# =====================================================
# Recursive helper → get ALL descendant category IDs
# =====================================================

def get_all_children(category):
    ids = []
    for child in category.children.all():
        ids.append(child.id)
        ids.extend(get_all_children(child))
    return ids


# =====================================================
# HOME PAGE
# =====================================================

def home(request):

    query = request.GET.get("q")

    categories = Category.objects.filter(parent__isnull=True)

    products = Product.objects.filter(status="approved")

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    now = timezone.now()
    # Find active live sale first, then nearest upcoming sale
    active_sale = (
        Sale.objects.filter(is_active=True, start_datetime__lte=now, end_datetime__gte=now).first()
        or Sale.objects.filter(is_active=True, start_datetime__gt=now).order_by('start_datetime').first()
    )
    sale_ads = []
    sale_ads_json = '[]'
    sale_end_iso = ''
    if active_sale:
        sale_ads = list(
            SaleAdvertisement.objects.filter(sale=active_sale, is_approved=True)
            .select_related('product')
        )
        sale_ads_json = json.dumps([
            {
                'product_id': a.product.id,
                'product_name': a.product.name,
                'ad_image': a.ad_image.url,
            }
            for a in sale_ads
        ])
        # Countdown target: end if live, start if upcoming
        countdown_target = active_sale.end_datetime if active_sale.is_live else active_sale.start_datetime
        sale_end_iso = countdown_target.isoformat()

    return render(request, "products/home.html", {
        "categories": categories,
        "products": products,
        "active_sale": active_sale,
        "sale_ads_json": sale_ads_json,
        "sale_end_iso": sale_end_iso,
        "recommended_products": (
            __import__("recommender.services", fromlist=["get_recommendations_for_user"])
            .get_recommendations_for_user(request.user, limit=12)
            if request.user.is_authenticated
            else []
        ),
    })


# =====================================================
# CATEGORY PAGE
# =====================================================

def category_page(request, slug):
    from .models import Attribute, VariantAttributeValue, ProductVariant
    from django.db.models import Min, Max

    category = get_object_or_404(Category, slug=slug)
    sub_categories = category.children.prefetch_related("children").all()

    child_ids = get_all_children(category)
    child_ids.append(category.id)

    base_qs = Product.objects.filter(category_id__in=child_ids, status="approved")

    # ── Price filter ──────────────────────────────────────────────
    price_stats = ProductVariant.objects.filter(product__in=base_qs).aggregate(
        min_price=Min("price"), max_price=Max("price")
    )
    global_min = int(price_stats["min_price"] or 0)
    global_max = int(price_stats["max_price"] or 10000)

    sel_min = request.GET.get("price_min", global_min)
    sel_max = request.GET.get("price_max", global_max)
    try:
        sel_min = int(sel_min)
        sel_max = int(sel_max)
    except (ValueError, TypeError):
        sel_min, sel_max = global_min, global_max

    # ── Collect filterable attributes that exist on these products ─
    attr_values_qs = (
        VariantAttributeValue.objects
        .filter(variant__product__in=base_qs, attribute__is_filterable=True)
        .select_related("attribute", "attribute_value")
        .order_by("attribute__name", "attribute_value__value")
    )

    # Build {attr_name: {slug, values:[{value, slug}]}} deduplicated
    from collections import OrderedDict
    filter_attrs = OrderedDict()
    for av in attr_values_qs:
        a = av.attribute
        v = av.attribute_value
        if a.name not in filter_attrs:
            filter_attrs[a.name] = {"slug": a.slug, "values": OrderedDict()}
        filter_attrs[a.name]["values"][v.slug] = v.value

    # ── Apply attribute filters ───────────────────────────────────
    products = base_qs
    selected_filters = {}   # {attr_name: [value_slugs]}
    for attr_name, info in filter_attrs.items():
        param = f"attr_{info['slug']}"
        chosen = request.GET.getlist(param)
        if chosen:
            selected_filters[attr_name] = chosen
            products = products.filter(
                variants__attribute_values__attribute__slug=info["slug"],
                variants__attribute_values__attribute_value__slug__in=chosen,
            ).distinct()

    # ── Apply price filter ────────────────────────────────────────
    products = products.filter(
        variants__price__gte=sel_min,
        variants__price__lte=sel_max,
    ).distinct()

    # ── Sort ─────────────────────────────────────────────────────
    sort = request.GET.get("sort", "")
    if sort == "price_asc":
        products = products.order_by("variants__price")
    elif sort == "price_desc":
        products = products.order_by("-variants__price")
    elif sort == "newest":
        products = products.order_by("-created_at")

    # convert filter_attrs to list for template
    filter_attrs_list = [
        {"name": k, "slug": v["slug"], "values": [{"slug": s, "value": lbl} for s, lbl in v["values"].items()]}
        for k, v in filter_attrs.items()
    ]

    # flat set of all selected attribute value slugs (for checkbox checked state)
    selected_slugs = set()
    for slugs in selected_filters.values():
        selected_slugs.update(slugs)

    return render(request, "products/category_page.html", {
        "parent": category,
        "sub_categories": sub_categories,
        "products": products,
        "filter_attrs": filter_attrs_list,
        "selected_filters": selected_filters,
        "selected_slugs": selected_slugs,
        "global_min": global_min,
        "global_max": global_max,
        "sel_min": sel_min,
        "sel_max": sel_max,
        "sort": sort,
        "total_products": products.count(),
    })


# =====================================================
# PRODUCT DETAIL
# =====================================================


def product_detail(request, id):

    product = get_object_or_404(
    Product.objects.select_related("category", "vendor"),
    id=id
)
    

    # ✅ Track user view interaction (for recommendation system)
    if request.user.is_authenticated:
        UserInteraction.objects.create(
            user=request.user,
            product_id=product.id,
            action_type="view",
            score=1,
        )
    # ✅ Optimized variant query
    variants = ProductVariant.objects.filter(product=product).prefetch_related(
        "images",
        "attribute_values__attribute",
        "attribute_values__attribute_value"
    )

    base_images = product.image if product.image else []

    colors = {}
    flat_variants = []

    for v in variants:

        price = float(v.price)
        stock = v.stock

        color_val = None
        other_vals = []

        for av in v.attribute_values.all():

            value = av.attribute_value.value
            slug = av.attribute.slug.lower().strip()
            name = av.attribute.name

            if slug in ("color", "colour"):
                color_val = value
            else:
                other_vals.append({
                    "attr": name,
                    "value": value
                })

        variant_label = (
            " / ".join(x["value"] for x in other_vals)
            if other_vals
            else (color_val or "Default")
        )

        vimgs = [img.image.url for img in v.images.all()]

        entry = {
            "id": v.id,
            "label": variant_label,
            "price": price,
            "stock": stock,
            "images": vimgs,
            "attrs": {ov["attr"]: ov["value"] for ov in other_vals},
        }

        # =========================
        # COLOR GROUPING LOGIC
        # =========================
        if color_val:

            if color_val not in colors:
                colors[color_val] = {
                    "name": color_val,
                    "swatch": vimgs[0] if vimgs else (
                        base_images[0] if base_images else ""
                    ),
                    "images": vimgs if vimgs else base_images,
                    "dims": {},
                    "variants": []
                }

            # Merge attribute dimension values
            for ov in other_vals:
                dim = ov["attr"]
                val = ov["value"]

                dims = colors[color_val]["dims"]

                if dim not in dims:
                    dims[dim] = []

                if val not in dims[dim]:
                    dims[dim].append(val)

            colors[color_val]["variants"].append(entry)

        else:
            flat_variants.append(entry)

    # =========================
    # CONTEXT
    # =========================
    # =====================================================
    # RELATED / RECOMMENDED PRODUCTS
    # Collaborative: users who touched this product also touched these
    # =====================================================
    user_ids = (
        UserInteraction.objects.filter(product_id=product.id)
        .values_list("user_id", flat=True)
        .distinct()
    )

    collab_ids = list(
        UserInteraction.objects.filter(user_id__in=user_ids)
        .exclude(product_id=product.id)
        .values("product_id")
        .annotate(cnt=Count("product_id"))
        .order_by("-cnt")
        .values_list("product_id", flat=True)[:8]
    )

    related_products = list(
        Product.objects.filter(
            id__in=collab_ids,
            status="approved",
            is_active=True,
        ).prefetch_related("variants")
    )

    # Fallback: same-category products when collaborative data is thin
    if len(related_products) < 4 and product.category:
        existing_ids = [p.id for p in related_products] + [product.id]
        fallback = list(
            Product.objects.filter(
                category=product.category,
                status="approved",
                is_active=True,
            )
            .exclude(id__in=existing_ids)
            .prefetch_related("variants")[: 8 - len(related_products)]
        )
        related_products += fallback

    # ── Frequently Bought Together ────────────────────────────────
    from recommender.services import get_fbt_products
    fbt_products = get_fbt_products(product.id, limit=4)

    # Build FBT bundle price (main + companions cheapest variant)
    def _cheapest_price(p):
        v = p.variants.filter(stock__gt=0).first() or p.variants.first()
        return float(v.price) if v else 0.0

    fbt_items = []
    fbt_total = _cheapest_price(product)
    for fp in fbt_products:
        price = _cheapest_price(fp)
        img = fp.image[0] if fp.image else None
        fbt_items.append({"product": fp, "price": price, "image": img})
        fbt_total += price

    context = {
        "product": product,
        "colors_json": json.dumps(list(colors.values())),
        "flat_variants_json": json.dumps(flat_variants),
        "base_images_json": json.dumps(base_images),
        "product_attributes": product.attributes
            .select_related("attribute")
            .order_by("attribute__name"),
        "spec_attrs": product.attributes
            .select_related("attribute")
            .filter(attribute__section="specs")
            .order_by("attribute__name"),
        "mfr_attrs": product.attributes
            .select_related("attribute")
            .filter(attribute__section="manufacturer")
            .order_by("attribute__name"),
        "related_products": related_products,
        "fbt_items": fbt_items,
        "fbt_main_price": _cheapest_price(product),
        "fbt_total": round(fbt_total, 2),
    }

    # ---- Bundles: build enriched display data ----
    bundles_display = []
    for _b in Bundle.objects.filter(products=product, is_active=True).prefetch_related(
        'bundle_items',
        Prefetch('products', queryset=Product.objects.prefetch_related(
            Prefetch('variants', queryset=ProductVariant.objects.prefetch_related('images'))
        ))
    ):
        _items = []
        _orig = 0
        _disc_total = 0
        _discount_map = {}
        for _bp in _b.bundle_items.all():
            if _bp.discounted_price is not None:
                _discount_map[_bp.product_id] = float(_bp.discounted_price)

        _bundle_products = sorted(
            list(_b.products.all()),
            key=lambda p: (0 if p.id == product.id else 1, p.name.lower())
        )
        for _p in _bundle_products:
            _v = _p.variants.filter(stock__gt=0).first() or _p.variants.first()
            if _v:
                _old_price = float(_v.price)
                _discounted = _discount_map.get(_p.id)
                if _discounted is None or _discounted <= 0:
                    _discounted = _old_price

                _img = ('/media/' + _p.image[0]) if _p.image else (
                    _v.images.first().image.url if _v.images.exists() else ''
                )
                _items.append({
                    'product': _p,
                    'variant': _v,
                    'image': _img,
                    'old_price': _old_price,
                    'discounted_price': _discounted,
                    'is_main': _p.id == product.id,
                })
                _orig += _old_price
                _disc_total += _discounted
        if _items:
            _bundle_price = float(_b.bundle_price) if _b.bundle_price else _disc_total
            bundles_display.append({
                'bundle': _b, 'items': _items,
                'orig_total': round(_orig, 2),
                'bundle_total': round(_bundle_price, 2),
                'savings': round(max(_orig - _bundle_price, 0), 2),
            })
    context['bundles_display'] = bundles_display

    return render(request, "products/product_details.html", context)


# =====================================================
# TRACK INTERACTION  (AJAX POST — anonymous-safe)
# Records user behaviour signals for the AI recommender.
# =====================================================

_VALID_ACTIONS = {"search", "view", "click", "cart", "purchase"}
_ACTION_SCORES = {"search": 1, "view": 2, "click": 3, "cart": 5, "purchase": 10}


@require_POST
def track_interaction(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "reason": "unauthenticated"})

    try:
        body       = json.loads(request.body)
        product_id = int(body.get("product_id", 0))
        action     = str(body.get("action", "")).lower().strip()
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "reason": "bad payload"}, status=400)

    if action not in _VALID_ACTIONS or product_id <= 0:
        return JsonResponse({"ok": False, "reason": "invalid"}, status=400)

    if not Product.objects.filter(id=product_id, status="approved", is_active=True).exists():
        return JsonResponse({"ok": False, "reason": "product not found"}, status=404)

    from recommender.models import UserInteraction
    UserInteraction.objects.create(
        user=request.user,
        product_id=product_id,
        action_type=action,
        score=_ACTION_SCORES[action],
    )
    return JsonResponse({"ok": True})


# =====================================================
# SUBMIT REVIEW (AJAX POST)
# =====================================================

@login_required
def submit_review(request, product_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)

    product = get_object_or_404(Product, id=product_id)

    if Review.objects.filter(product=product, user=request.user).exists():
        return JsonResponse({"success": False, "error": "You have already reviewed this product."})

    try:
        rating = int(request.POST.get("rating", 5))
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "error": "Invalid rating."})

    if not (1 <= rating <= 5):
        return JsonResponse({"success": False, "error": "Rating must be between 1 and 5."})

    comment = request.POST.get("comment", "").strip()
    if not comment:
        return JsonResponse({"success": False, "error": "Please write a review comment."})

    review = Review.objects.create(
        product=product,
        user=request.user,
        rating=rating,
        comment=comment,
        approved=False,
    )

    images = request.FILES.getlist("images")
    main_image_url = ""
    if images:
        review.image = images[0]
        review.save()
        main_image_url = review.image.url
        for i, img in enumerate(images[1:], start=1):
            ReviewImage.objects.create(review=review, image=img, order=i)

    extra_urls = [ri.image.url for ri in review.extra_images.all()]

    return JsonResponse({
        "success": True,
        "review": {
            "id": review.id,
            "user": request.user.get_full_name() or request.user.username,
            "rating": review.rating,
            "comment": review.comment,
            "created": review.created.strftime("%b %d, %Y"),
            "images": ([main_image_url] if main_image_url else []) + extra_urls,
        },
    })


# =====================================================
# LOAD REVIEWS (AJAX GET)
# =====================================================

def load_reviews(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews_qs = Review.objects.filter(
        product=product, approved=True
    ).select_related("user").prefetch_related("extra_images").order_by("-created")

    total = reviews_qs.count()
    avg = round(sum(r.rating for r in reviews_qs) / total, 1) if total else 0

    dist = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    reviews_data = []

    # Need fresh iteration — annotate dist
    for r in reviews_qs:
        dist[r.rating] = dist.get(r.rating, 0) + 1
        imgs = []
        if r.image:
            imgs.append(r.image.url)
        for ei in r.extra_images.all():
            imgs.append(ei.image.url)
        reviews_data.append({
            "id": r.id,
            "user": r.user.get_full_name() or r.user.username,
            "rating": r.rating,
            "comment": r.comment,
            "created": r.created.strftime("%b %d, %Y"),
            "images": imgs,
        })

    return JsonResponse({
        "total": total,
        "avg": avg,
        "distribution": dist,
        "reviews": reviews_data,
        "user_reviewed": (
            Review.objects.filter(product=product, user=request.user).exists()
            if request.user.is_authenticated else False
        ),
    })


# =====================================================
# SEARCH SUGGESTIONS
# =====================================================



# =====================================================
# SMART SEARCH SUGGESTIONS  (NLP-powered autocomplete)
# =====================================================

def search_suggestions(request):
    raw = request.GET.get("q", "").strip()

    if len(raw) < 2:
        return JsonResponse({"products": [], "categories": [], "brands": [], "trending": []})

    # ── Log query for trending analysis (only for queries of 3+ chars) ──
    if len(raw) >= 3:
        try:
            if not request.session.session_key:
                request.session.create()
            SearchQuery.objects.create(
                query=raw.lower(),
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key or "",
            )
        except Exception:
            pass

    tokens   = _tokenize(raw)
    expanded = _expand_tokens(tokens)

    # Build Q filter from expanded tokens (OR across tokens, AND across fields)
    q_filter = Q()
    for token in expanded:
        q_filter |= (
            Q(name__icontains=token) |
            Q(brand__icontains=token) |
            Q(short_description__icontains=token)
        )

    # ── Products ──────────────────────────────────────────────────────
    candidates = (
        Product.objects
        .filter(q_filter, status="approved", is_active=True)
        .select_related("category")
        .prefetch_related("variants")
        .distinct()[:30]
    )

    scored = []
    for p in candidates:
        sc = _nlp_product_score(p, tokens)
        prices = [v.price for v in p.variants.all()]
        min_price = min(prices) if prices else None
        scored.append((sc, p, min_price))

    scored.sort(key=lambda x: -x[0])

    product_results = []
    for _, p, min_price in scored[:6]:
        img = p.image[0] if p.image else None
        product_results.append({
            "id":       p.id,
            "name":     p.name,
            "brand":    p.brand or "",
            "slug":     p.slug or "",
            "image":    img,
            "price":    str(min_price) if min_price else None,
            "category": p.category.name if p.category else "",
        })

    # ── Categories ───────────────────────────────────────────────────
    cat_q = Q()
    for token in expanded:
        cat_q |= Q(name__icontains=token)

    categories = (
        Category.objects
        .filter(cat_q)
        .annotate(
            product_count=Count(
                "product",
                filter=Q(product__status="approved", product__is_active=True),
            )
        )
        .order_by("-product_count")[:5]
    )
    cat_results = [{"name": c.name, "slug": c.slug, "count": c.product_count} for c in categories]

    # ── Brands ───────────────────────────────────────────────────────
    brand_q = Q()
    for token in expanded:
        brand_q |= Q(brand__icontains=token)

    brands = (
        Product.objects
        .filter(brand_q, status="approved", is_active=True)
        .exclude(brand="")
        .values("brand")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )
    brand_results = [{"name": b["brand"], "count": b["count"]} for b in brands]

    # ── Trending (last 7 days) ────────────────────────────────────────
    week_ago = timezone.now() - timedelta(days=7)
    trending_qs = (
        SearchQuery.objects
        .filter(timestamp__gte=week_ago)
        .values("query")
        .annotate(count=Count("id"))
        .order_by("-count")[:8]
    )
    trending_results = [t["query"] for t in trending_qs]

    return JsonResponse({
        "products":   product_results,
        "categories": cat_results,
        "brands":     brand_results,
        "trending":   trending_results,
    })


# =====================================================
# SEARCH INDEX  (cached lightweight payload for
# client-side instant filtering in the browser)
# =====================================================

def search_index(request):
    """
    Returns a compact JSON index of all approved products, categories,
    and brands.  Cached for 15 minutes so the browser can do instant
    prefix-matching locally while the debounced NLP call is in-flight.
    """
    CACHE_KEY = "smart_search_index_v2"
    data = cache.get(CACHE_KEY)

    if data is None:
        products = list(
            Product.objects
            .filter(status="approved", is_active=True)
            .values("id", "name", "brand", "slug")
        )
        categories = list(Category.objects.values("name", "slug"))
        brands = list(
            Product.objects
            .filter(status="approved", is_active=True)
            .exclude(brand="")
            .values_list("brand", flat=True)
            .distinct()
        )
        data = {"products": products, "categories": categories, "brands": brands}
        cache.set(CACHE_KEY, data, 60 * 15)

    return JsonResponse(data)


# =====================================================
# VENDOR STEP 1 → ADD PRODUCT
# =====================================================

@login_required
def vendor_add_product(request):

    categories = Category.objects.filter(parent__isnull=True)

    if request.method == "POST":

        product = Product.objects.create(
            vendor=request.user,
            name=request.POST.get("name"),
            description=request.POST.get("description"),
            category_id=request.POST.get("category"),
            status="pending"
        )

        for key, value in request.POST.items():
            if key.startswith("price_"):
                size = key.replace("price_", "")
                price = value
                stock = request.POST.get(f"stock_{size}", 0)

                ProductVariant.objects.create(
                    product=product,
                    sku=f"{product.id}-{uuid.uuid4().hex[:8]}",
                    price=price,
                    stock=stock
                )
        if "save_another" in request.POST:
            return redirect("/products/vendor/add/?new=1")

        return redirect("home")

    return render(request,"vendor/add_product.html",{
        "categories":categories
    })


# =====================================================
# VENDOR STEP 2 → ADD COLOR + IMAGES
# =====================================================

@login_required
def vendor_add_color(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":

        color = request.POST.get("color")
        images = request.FILES.getlist("images")

        # Images are stored via VariantImage; variants are created in the sizes step
        return redirect("vendor_add_sizes", product.id, color)

    return render(request, "vendor/add_color.html", {
        "product": product
    })


# =====================================================
# VENDOR STEP 3 → ENTER MULTIPLE SIZES
# =====================================================

@login_required
def vendor_add_sizes(request, product_id, color):

    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":

        sizes = request.POST.get("sizes").split(",")

        return render(request, "vendor/variant_prices.html", {
            "sizes": sizes,
            "product": product,
            "color": color
        })

    return render(request, "vendor/add_sizes.html")


# =====================================================
# VENDOR STEP 4 → SAVE VARIANT PRICES
# =====================================================

@login_required
def save_variants(request, product_id, color):

    product = get_object_or_404(Product, id=product_id)

    for k, v in request.POST.items():
        if k.startswith("price_"):

            size = k.replace("price_", "")
            price = v
            stock = request.POST.get(f"stock_{size}")

            ProductVariant.objects.create(
                product=product,
                sku=f"{product.id}-{uuid.uuid4().hex[:8]}",
                price=price,
                stock=stock
            )

    return redirect("vendor_add_color", product.id)

def variant_price(request):
    """
    AJAX endpoint:
    returns price + stock for selected variant
    """

    product_id = request.GET.get("product")
    attribute_id = request.GET.get("attribute")
    value = request.GET.get("value")

    try:
        vav = VariantAttributeValue.objects.select_related("variant").get(
            variant__product_id=product_id,
            attribute_id=attribute_id,
            attribute_value__value=value
        )
        variant = vav.variant

        return JsonResponse({
            "success": True,
            "price": float(variant.price),
            "stock": variant.stock
        })

    except (VariantAttributeValue.DoesNotExist, ProductVariant.DoesNotExist):

        return JsonResponse({
            "success": False,
            "price": 0,
            "stock": 0
        })

# =====================================================
# ADVANCED CHATBOT API
# =====================================================

@csrf_exempt
@require_POST
def chatbot_api(request):
    """
    POST /chatbot/
    Body: {"message": "..."}
    Response: {"answer": "<html string>"}
    """
    try:
        body = json.loads(request.body)
        message = body.get('message', '').strip()
    except Exception:
        return JsonResponse({'answer': 'Invalid request.'}, status=400)

    if not message:
        return JsonResponse({'answer': 'Please type a message.'})

    lower = message.lower()

    # ── 1. Greetings (instant local reply) ──────────────────────────
    greet_keys = ['hello', 'hi', 'hey', 'hii', 'good morning', 'good evening', 'namaste', 'helo']
    if any(k in lower for k in greet_keys):
        return JsonResponse({'answer': "<strong>Hello!</strong> I'm your E‑Commerce Assistant. Ask me about any product, order, payment, shipping, returns, or anything else!"})

    thanks_keys = ['thank', 'thanks', 'great', 'awesome', 'helpful', 'nice']
    if any(k in lower for k in thanks_keys):
        return JsonResponse({'answer': " You're welcome! Is there anything else I can help you with?"})

    bye_keys = ['bye', 'goodbye', 'see you', 'no thanks', 'ok done']
    if any(k in lower for k in bye_keys):
        return JsonResponse({'answer': " Goodbye! Have a great shopping experience! "})

    # ── 2. Product Search ─────────────────────────────────────────────
    # Extract a meaningful search term (strip common filler words)
    filler = {'tell me about', 'what is', 'what are', 'show me', 'describe', 'details of',
              'info about', 'information about', 'about', 'the', 'a ', 'an ', 'price of',
              'cost of', 'how much is', 'is', 'available', 'in stock', 'stock of', 'specs of',
              'specification of', 'features of', 'review of', 'reviews of'}
    search_term = lower
    for f in sorted(filler, key=len, reverse=True):
        search_term = search_term.replace(f, ' ')
    search_term = ' '.join(search_term.split()).strip()

    # Try to match products from DB
    product_qs = Product.objects.filter(
        Q(name__icontains=search_term) |
        Q(brand__icontains=search_term) |
        Q(short_description__icontains=search_term) |
        Q(description__icontains=search_term),
        status='approved',
        is_active=True,
    ).select_related('category').prefetch_related(
        'variants__attribute_values__attribute',
        'variants__attribute_values__attribute_value',
    ).distinct()[:3]

    if not product_qs.exists() and len(search_term) > 2:
        # Broader word-by-word search
        words = [w for w in search_term.split() if len(w) > 2]
        q_obj = Q()
        for w in words:
            q_obj |= Q(name__icontains=w) | Q(brand__icontains=w)
        product_qs = Product.objects.filter(
            q_obj, status='approved', is_active=True
        ).select_related('category').prefetch_related(
            'variants__attribute_values__attribute',
            'variants__attribute_values__attribute_value',
        ).distinct()[:3]

    if product_qs.exists():
        cards = []
        for product in product_qs:
            variants = list(product.variants.all())
            prices = [float(v.price) for v in variants]
            total_stock = sum(v.stock for v in variants)

            colors, sizes, other_attrs = set(), set(), {}
            for v in variants:
                for av in v.attribute_values.all():
                    slug = av.attribute.slug.lower().strip()
                    val = av.attribute_value.value
                    if slug in ('color', 'colour'):
                        colors.add(val)
                    elif slug == 'size':
                        sizes.add(val)
                    else:
                        other_attrs.setdefault(av.attribute.name, set()).add(val)

            if prices:
                mn, mx = min(prices), max(prices)
                price_str = f'₹{mn:,.0f}' if mn == mx else f'₹{mn:,.0f} – ₹{mx:,.0f}'
            else:
                price_str = 'Price not listed'

            stock_badge = (
                f'<span style="color:#16a34a;font-weight:600;">In Stock ({total_stock} units)</span>'
                if total_stock > 0 else
                '<span style="color:#dc2626;font-weight:600;"> Out of Stock</span>'
            )

            rows = []
            rows.append(f'<strong style="font-size:14px;">{product.name}</strong>')
            if product.brand:
                rows.append(f'<strong>Brand :</strong> {product.brand}')
            rows.append(f'<strong>Category :</strong> {product.category.name}')
            rows.append(f'<strong>Price :</strong> {price_str}')
            rows.append(f'<strong>Stock :</strong> {stock_badge}')
            if colors:
                rows.append(f'<strong>Colors :</strong> {", ".join(sorted(colors))}')
            if sizes:
                rows.append(f'<strong>Sizes :</strong> {", ".join(sorted(sizes))}')
            for attr_name, vals in other_attrs.items():
                rows.append(f'<strong>{attr_name} :</strong> {", ".join(sorted(vals))}')
            if product.short_description:
                rows.append(f'<strong>Summary :</strong> {product.short_description}')
            if product.description:
                desc = product.description.strip()
                short = desc[:400] + ('…' if len(desc) > 400 else '')
                rows.append(f'<strong>Description :</strong> {short}')
            rows.append(f'<a href="/product/{product.id}/" style="color:#2563eb;font-weight:700;text-decoration:none;">View Full Product Page →</a>')

            cards.append('<br>'.join(rows))

        if len(cards) == 1:
            return JsonResponse({'answer': cards[0]})
        sep = '<br><hr style="border:none;border-top:1px solid #e2e8f0;margin:8px 0;"><br>'
        header = f'<strong>Found {len(cards)} matching products:</strong><br><br>'
        return JsonResponse({'answer': header + sep.join(cards)})

    # ── 3. General E-Commerce KB ──────────────────────────────────────
    GENERAL_KB = [
        (['track', 'order status', 'where is my order', 'order tracking'],
         '<strong>Order Tracking</strong><br>Go to <a href="/orders/my-orders/" style="color:#2563eb;">My Orders</a> to see real-time status. You\'ll see Pending, Accepted, Shipped, or Delivered.'),
        (['return', 'refund', 'money back', 'exchange', 'replace'],
         '↩ <strong>Returns & Refunds</strong><br>Returns accepted within <strong>7 days</strong> of delivery for unused items in original packaging. Visit <a href="/orders/my-orders/" style="color:#2563eb;">My Orders</a> to raise a return request.'),
        (['shipping', 'delivery time', 'how long', 'dispatch', 'courier', 'arrive'],
         '<strong>Shipping Info</strong><br>Standard delivery: <strong>3–5 business days</strong>. Express (1–2 days) available at checkout. Free shipping on orders above ₹499.'),
        (['payment', 'pay', 'failed payment', 'card', 'upi', 'wallet', 'transaction', 'charged twice'],
         ' <strong>Payment Help</strong><br>We accept UPI, Debit/Credit Cards, and Net Banking. A failed-payment refund auto-reverses in <strong>5–7 business days</strong>. Contact support if it doesn\'t.'),
        (['cancel', 'cancellation', 'cancel order'],
         ' <strong>Cancel Order</strong><br>Orders can be cancelled before shipment. Go to <a href="/orders/my-orders/" style="color:#2563eb;">My Orders</a> → select order → <em>Cancel</em>. Post-shipment cancellations are not possible.'),
        (['account', 'login', 'password', 'forgot password', 'register', 'signup'],
         ' <strong>Account Help</strong><br>Forgot password? Go to the <a href="/accounts/login/" style="color:#2563eb;">Login page</a> → <em>Forgot Password</em>. For sign-up issues, ensure your email isn\'t already registered.'),
        (['coupon', 'discount', 'promo', 'offer', 'deal', 'promo code'],
         ' <strong>Coupons & Offers</strong><br>Enter your coupon in the <em>Promo Code</em> field at checkout. Check the homepage  Deals section for the latest offers.'),
        (['cart', 'add to cart', 'basket', 'checkout'],
         ' <strong>Cart & Checkout</strong><br>Add items to your cart and click the cart icon to review. Make sure you\'re logged in before placing an order.'),
        (['vendor', 'sell', 'become vendor', 'seller', 'open shop'],
         ' <strong>Become a Vendor</strong><br>Register an account and select <em>Vendor</em> as your role. After admin approval, you can start listing products from the Vendor Dashboard.'),
        (['contact', 'support', 'help', 'email', 'phone', 'reach us', 'human agent'],
         ' <strong>Contact Support</strong><br>Available <strong>Mon–Sat, 9am–6pm</strong>.<br> <a href="mailto:support@ecommerce.com" style="color:#2563eb;">support@ecommerce.com</a><br>We typically respond within 24 hours.'),
    ]

    for keys, answer in GENERAL_KB:
        if any(k in lower for k in keys):
            return JsonResponse({'answer': answer})

    # ── 4. Fallback ───────────────────────────────────────────────────
    return JsonResponse({
        'answer': (
            " I couldn't find a product matching <em>\"" + message[:60] + "\"</em>.<br><br>"
            "Try searching with the product's exact name or brand. You can also:<br>"
            "• Browse our <a href='/' style='color:#2563eb;'>Homepage</a><br>"
            "• <a href='mailto:support@ecommerce.com' style='color:#2563eb;'>Email support</a>"
        )
    })


def product_list(request):

    products = Product.objects.filter(
        is_active=True,
        status="approved"
    ).prefetch_related(
        "variants__images"
    )

    return render(request, "product_list.html", {
        "products": products
    })