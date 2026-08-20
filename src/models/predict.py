# src/models/predict.py

import joblib
import pandas as pd

from src.config.config import MODEL_PATH, FEATURE_COLUMNS


# -----------------------------
# Load trained model
# -----------------------------
def load_model():
    return joblib.load(MODEL_PATH)


# -----------------------------
# Predict Burnout
# -----------------------------
def predict_burnout(input_dict: dict):

    model = load_model()

    # Convert input to DataFrame
    input_df = pd.DataFrame([input_dict])

    # Ensure correct feature order
    input_df = input_df[FEATURE_COLUMNS]

    # Prediction
    prediction = model.predict(input_df)[0]

    # Probability (useful for dashboard)
    probability = model.predict_proba(input_df)[0][1]

    return {
        "prediction": int(prediction),
        "burnout_probability": float(probability)
    }