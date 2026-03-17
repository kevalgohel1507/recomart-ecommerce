"""
recommender/services.py
-----------------------
All recommendation and FBT business-logic lives here.
"""
from collections import defaultdict

from recommender.utils import load_model
from recommender.models import UserRecommendation, FrequentlyBoughtTogether, UserInteraction, INTERACTION_SCORES
from products.models import ProductRelation


# ── ALS / Collaborative Filtering ─────────────────────────────────────────────

def generate_recommendations(matrix, model, encoders):
    """Write collaborative-filtering recommendations to UserRecommendation table."""
    for user_index, user_id in encoders["user_map"].items():
        try:
            recs = model.recommend(
                user_index,
                matrix[user_index],
                N=12,
                filter_already_liked_items=True,
            )
        except Exception:
            continue

        for product_index, score in recs:
            product_id = encoders["product_map"].get(product_index)
            if product_id is None:
                continue
            UserRecommendation.objects.update_or_create(
                user_id=user_id,
                product_id=product_id,
                defaults={"score": float(score), "algorithm": "als"},
            )


# ── Cross-sell (ProductRelation) ──────────────────────────────────────────────

def get_cross_sell_products(product_id, limit=6):
    relations = ProductRelation.objects.filter(
        product_id=product_id
    ).order_by("-score")[:limit]
    return [r.related_product for r in relations]


# ── Frequently Bought Together ────────────────────────────────────────────────

def compute_fbt_scores():
    """
    Scan all purchase interactions and rebuild the FrequentlyBoughtTogether table.

    Algorithm:
    1. Collect every product each user has purchased.
    2. For each pair (a, b) co-purchased by the same user → increment co_count.
    3. Normalise score = co_count / sqrt(freq_a * freq_b)  (Jaccard-like).
    4. Upsert rows into FrequentlyBoughtTogether (bidirectional).
    """
    purchases = UserInteraction.objects.filter(
        action_type="purchase"
    ).values("user_id", "product_id")

    user_purchases: dict[int, set] = defaultdict(set)
    product_freq:   dict[int, int] = defaultdict(int)

    for row in purchases:
        uid = row["user_id"]
        pid = row["product_id"]
        user_purchases[uid].add(pid)
        product_freq[pid] += 1

    co_count: dict[tuple, int] = defaultdict(int)
    for uid, pids in user_purchases.items():
        plist = sorted(pids)
        for i in range(len(plist)):
            for j in range(i + 1, len(plist)):
                co_count[(plist[i], plist[j])] += 1

    import math
    updated = 0
    for (pid_a, pid_b), count in co_count.items():
        denom = math.sqrt(product_freq[pid_a] * product_freq[pid_b])
        norm_score = count / denom if denom else float(count)

        for src, dst in [(pid_a, pid_b), (pid_b, pid_a)]:
            FrequentlyBoughtTogether.objects.update_or_create(
                product_id=src,
                related_product_id=dst,
                defaults={"co_purchase_count": count, "score": norm_score},
            )
            updated += 1

    return updated


def get_fbt_products(product_id, limit=4):
    """Return top FBT companion products for a given product_id."""
    from products.models import Product

    fbt_ids = list(
        FrequentlyBoughtTogether.objects
        .filter(product_id=product_id)
        .order_by("-score")
        .values_list("related_product_id", flat=True)[:limit]
    )

    if not fbt_ids:
        return []

    id_order = {pid: idx for idx, pid in enumerate(fbt_ids)}
    products = list(
        Product.objects
        .filter(id__in=fbt_ids, status="approved", is_active=True)
        .prefetch_related("variants")
    )
    products.sort(key=lambda p: id_order.get(p.id, 999))
    return products


# ── Content-based fallback (category similarity) ──────────────────────────────

def get_content_based_recs(user, limit=10):
    """
    When collaborative data is thin, recommend products from categories the
    user has most interacted with.
    """
    from products.models import Product, Category

    # Which categories has the user interacted with most?
    cat_scores: dict[int, float] = defaultdict(float)
    interactions = (
        UserInteraction.objects
        .filter(user=user)
        .values("product_id", "action_type")
    )
    product_cache: dict[int, int] = {}

    def _get_cat(pid):
        if pid not in product_cache:
            try:
                product_cache[pid] = Product.objects.get(id=pid).category_id
            except Product.DoesNotExist:
                product_cache[pid] = None
        return product_cache[pid]

    for row in interactions:
        cat_id = _get_cat(row["product_id"])
        if cat_id:
            cat_scores[cat_id] += INTERACTION_SCORES.get(row["action_type"], 1)

    if not cat_scores:
        return list(
            Product.objects
            .filter(status="approved", is_active=True)
            .order_by("-created_at")
            .prefetch_related("variants")[:limit]
        )

    top_cats = sorted(cat_scores, key=lambda c: -cat_scores[c])[:5]
    seen_ids = set(product_cache.keys())

    products = list(
        Product.objects
        .filter(category_id__in=top_cats, status="approved", is_active=True)
        .exclude(id__in=seen_ids)
        .prefetch_related("variants")
        .order_by("-created_at")[:limit]
    )
    return products


# ── Hybrid recommendation ─────────────────────────────────────────────────────

def get_recommendations_for_user(user, limit=12):
    """
    Returns a ranked list of Products for 'Recommended For You' section.
    Strategy:
    - Primary: ALS collaborative-filtering scores from UserRecommendation table.
    - Fallback: content-based recs when ALS data is absent.
    """
    from products.models import Product

    cf_recs = list(
        UserRecommendation.objects
        .filter(user=user)
        .order_by("-score")
        .values_list("product_id", flat=True)[:limit]
    )

    if cf_recs:
        id_order = {pid: i for i, pid in enumerate(cf_recs)}
        products = list(
            Product.objects
            .filter(id__in=cf_recs, status="approved", is_active=True)
            .prefetch_related("variants")
        )
        products.sort(key=lambda p: id_order.get(p.id, 999))
        # Pad with content-based if too few
        if len(products) < 6:
            cb = get_content_based_recs(user, limit=limit - len(products))
            existing = {p.id for p in products}
            products += [p for p in cb if p.id not in existing]
        return products[:limit]

    return get_content_based_recs(user, limit=limit)
