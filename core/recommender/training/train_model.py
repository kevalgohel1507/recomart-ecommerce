"""
training/train_model.py
-----------------------
Trains an ALS (Alternating Least Squares) collaborative-filtering model on
weighted user-interaction data, then writes pre-computed recommendations to
the UserRecommendation table.

Algorithms used
---------------
1. Collaborative Filtering — ALS (implicit library)
   Fast matrix factorisation on implicit feedback (views, clicks, purchases).
2. The training data is weighted by action type (search=1, view=2, cart=5,
   purchase=10) so the model leans heavily on purchase signals.
"""
from implicit.als import AlternatingLeastSquares

from recommender.training.data_loader import load_interaction_data
from recommender.training.feature_engineering import create_matrix
from recommender.utils import save_model
from recommender.services import generate_recommendations


def train_model():
    df = load_interaction_data()

    if df is None:
        print("[Recommender] No interaction data — skipping training.")
        return None

    print(f"[Recommender] Training on {len(df)} (user, product) pairs …")

    matrix, encoders = create_matrix(df)

    # ── ALS (Collaborative Filtering + Matrix Factorisation) ──────────────────
    model = AlternatingLeastSquares(
        factors=64,           # latent dimensions (matrix factorisation rank)
        iterations=25,
        regularization=0.05,
        use_gpu=False,
    )
    model.fit(matrix)

    save_model(model, encoders)

    # Write recommendations to DB
    generate_recommendations(matrix, model, encoders)

    print("[Recommender] Model trained, saved, and recommendations updated.")
    return model, encoders
