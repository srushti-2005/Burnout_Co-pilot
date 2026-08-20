# src/features/feature_engineering.py

import pandas as pd

from src.config.config import (
    PROCESSED_DATA_PATH,
    USER_COLUMN,
    TIMESTAMP_COLUMN
)


# -----------------------------
# Load Processed Dataset
# -----------------------------
def load_processed_data():
    df = pd.read_csv(PROCESSED_DATA_PATH)

    # Ensure timestamp is datetime
    df[TIMESTAMP_COLUMN] = pd.to_datetime(df[TIMESTAMP_COLUMN])

    # Sort sessions per user
    df = df.sort_values([USER_COLUMN, TIMESTAMP_COLUMN])

    return df


# -----------------------------
# Session Index Feature
# -----------------------------
def create_session_index(df):
    df["session_index"] = df.groupby(USER_COLUMN).cumcount()
    return df


# -----------------------------
# Hour of Day Feature
# -----------------------------
def create_hour_feature(df):
    df["hour_of_day"] = df[TIMESTAMP_COLUMN].dt.hour
    return df


# -----------------------------
# Rolling CLI Mean
# -----------------------------
def create_rolling_cli(df):

    if "cli_score" not in df.columns:
        df["cli_score"] = (
            df["typing_variance"] +
            df["task_switching"] +
            df["late_night"]
        )

    df["rolling_cli"] = (
        df.groupby("user_id")["cli_score"]
        .rolling(5)
        .mean()
        .reset_index(level=0, drop=True)
    )

    return df


# -----------------------------
# Feature Engineering Pipeline
# -----------------------------
def run_feature_engineering():

    df = load_processed_data()

    df = create_session_index(df)

    df = create_hour_feature(df)

    df = create_rolling_cli(df)

    # Save updated dataset
    df.to_csv(PROCESSED_DATA_PATH, index=False)

    print("✅ Feature engineering complete")

    return df