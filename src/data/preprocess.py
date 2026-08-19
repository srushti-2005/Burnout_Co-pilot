# src/data/preprocess.py

from src.config.config import (
    RAW_DATA_PATH,
    PROCESSED_DATA_PATH,
    USER_COLUMN,
    TIMESTAMP_COLUMN
)

import pandas as pd
import os


RAW_PATH = RAW_DATA_PATH
PROCESSED_PATH = PROCESSED_DATA_PATH


def load_raw_data():
    df = pd.read_csv(RAW_PATH)
    return df


def clean_data(df):

    # 1️⃣ Drop duplicates
    df = df.drop_duplicates()

    # 2️⃣ Convert timestamp column to datetime
    if TIMESTAMP_COLUMN in df.columns:
        df[TIMESTAMP_COLUMN] = pd.to_datetime(df[TIMESTAMP_COLUMN])

    # 3️⃣ Sort sessions per user (VERY IMPORTANT)
    if USER_COLUMN in df.columns and TIMESTAMP_COLUMN in df.columns:
        df = df.sort_values([USER_COLUMN, TIMESTAMP_COLUMN])

    # 4️⃣ Handle missing values only if present
    if df.isnull().sum().sum() > 0:
        df = df.ffill()

    # 5️⃣ Ensure numeric columns are numeric
    numeric_cols = [
        "typing_speed",
        "error_rate",
        "task_switch_freq",
        "idle_time",
        "work_duration",
        "cli_score",
        "burnout_label",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 6️⃣ Final NA cleanup
    df = df.dropna()

    return df


def save_processed_data(df):
    os.makedirs("data/processed", exist_ok=True)
    df.to_csv(PROCESSED_PATH, index=False)


def run_preprocessing():
    df = load_raw_data()
    df_clean = clean_data(df)
    save_processed_data(df_clean)

    print("✅ Data preprocessing complete!")