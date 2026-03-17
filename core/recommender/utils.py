import os
import joblib
from django.conf import settings


MODEL_PATH = os.path.join(settings.BASE_DIR, "recommender/ml_models/als_model.pkl")
ENCODER_PATH = os.path.join(settings.BASE_DIR, "recommender/ml_models/encoders.pkl")


def save_model(model, encoders):
    joblib.dump(model, MODEL_PATH)
    joblib.dump(encoders, ENCODER_PATH)


def load_model():
    if not os.path.exists(MODEL_PATH):
        return None, None

    model = joblib.load(MODEL_PATH)
    encoders = joblib.load(ENCODER_PATH)

    return model, encoders