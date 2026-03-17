from django.db import models
from django.contrib.auth.models import User


# Weighted scores per action (used by training pipeline too)
INTERACTION_SCORES = {
    "search":   1,
    "view":     2,
    "click":    3,
    "cart":     5,
    "purchase": 10,
}


class UserInteraction(models.Model):
    ACTION_CHOICES = [
        ("search",   "Search"),
        ("view",     "View"),
        ("click",    "Click"),
        ("cart",     "Add To Cart"),
        ("purchase", "Purchase"),
    ]

    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name="interactions")
    product_id  = models.IntegerField(db_index=True)
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    score       = models.IntegerField()
    timestamp   = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "action_type"]),
            models.Index(fields=["product_id", "action_type"]),
        ]

    def __str__(self):
        return f"{self.user_id}-{self.product_id}-{self.action_type}"


class UserRecommendation(models.Model):
    """Stores pre-computed collaborative-filtering recommendations."""
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recommendations")
    product_id = models.IntegerField(db_index=True)
    score      = models.FloatField()
    algorithm  = models.CharField(max_length=30, default="als",
                                   help_text="als | mf | hybrid | content")
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "product_id")
        indexes = [
            models.Index(fields=["user", "score"]),
        ]

    def __str__(self):
        return f"{self.user_id}-{self.product_id}-{self.score:.2f}"


class FrequentlyBoughtTogether(models.Model):
    """
    Stores co-purchase relationships between products.
    Built by the compute_fbt management command from purchase history.
    """
    product         = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE,
        related_name="fbt_main"
    )
    related_product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE,
        related_name="fbt_as_companion"
    )
    co_purchase_count = models.PositiveIntegerField(default=1)
    score             = models.FloatField(default=0.0,
                                          help_text="Normalised co-purchase score")
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("product", "related_product")
        ordering        = ["-score"]
        indexes = [
            models.Index(fields=["product", "score"]),
        ]

    def __str__(self):
        return f"FBT: {self.product_id} ↔ {self.related_product_id} ({self.score:.2f})"