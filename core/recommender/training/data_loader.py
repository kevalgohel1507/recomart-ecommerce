import pandas as pd
from recommender.models import UserInteraction, INTERACTION_SCORES


def load_interaction_data():
    """
    Load all user interactions and aggregate into a single score per
    (user, product) pair.  Each action type has a different weight so
    purchases drive the model harder than mere views.
    """
    qs = UserInteraction.objects.all().values("user_id", "product_id", "action_type", "score")
    df = pd.DataFrame(list(qs))

    if df.empty:
        return None

    # Use the configured action-weight as a multiplier on the raw score
    df["action_weight"] = df["action_type"].map(INTERACTION_SCORES).fillna(1)
    df["weighted_score"] = df["score"] * df["action_weight"]

    # Aggregate: sum weighted scores per (user, product)
    df = (
        df.groupby(["user_id", "product_id"], as_index=False)["weighted_score"]
        .sum()
        .rename(columns={"weighted_score": "score"})
    )

    return df
