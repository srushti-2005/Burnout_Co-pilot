# src/models/train_model.py

import os
import joblib

from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split

from src.config.config import (
    MODEL_PATH,
    XGB_PARAMS,
    FEATURE_COLUMNS,
    TARGET_COLUMN,
)

from src.features.feature_engineering import load_processed_data

FEATURE_COLUMNS = [
    "typing_mean",
    "typing_variance",
    "task_switching",
    "work_duration",
    "late_night",
    "hour_of_day",
    "session_index"
]

def train_model():

    # Load dataset
    df = load_processed_data()

    # Select features and target
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    # Create model
    model = XGBClassifier(**XGB_PARAMS)

    # Train model
    model.fit(X_train, y_train)

    # Save model
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    print("✅ Model trained successfully!")
    print(f"Model saved at: {MODEL_PATH}")

    return model, X_test, y_test