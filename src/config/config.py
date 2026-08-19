# src/config/config.py

import os
from dotenv import load_dotenv

load_dotenv()

# ==============================
# SUPABASE CONFIG
# (values come from your .env file — see .env.example)
# ==============================
SUPABASE_URL              = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY         = os.environ.get("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")  # backend/FastAPI only, never in Streamlit

# ==============================
# PROJECT ROOT
# ==============================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

# ==============================
# DATA PATHS
# ==============================
RAW_DATA_PATH = os.path.join(PROJECT_ROOT, "data/raw/burnout_dataset.csv")
PROCESSED_DATA_PATH = os.path.join(PROJECT_ROOT, "data/processed/cleaned_data.csv")

# ==============================
# MODEL PATH
# ==============================
MODEL_PATH = os.path.join(PROJECT_ROOT, "models/model.pkl")

# ==============================
# OUTPUT PATH
# ==============================
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs")

# Ensure outputs directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================
# DATASET COLUMN NAMES
# (Used across pipeline)
# ==============================
USER_COLUMN = "user_id"
TIMESTAMP_COLUMN = "timestamp"

# ==============================
# TARGET COLUMN
# ⚠️ MUST match dataset exactly
# ==============================
TARGET_COLUMN = "burnout_label"

# ==============================
# FEATURE LIST
# ⚠️ VERY IMPORTANT
# Feature order must stay same
# ==============================
FEATURE_COLUMNS = [
    "typing_speed",
    "error_rate",
    "task_switch_freq",
    "idle_time",
    "work_duration",
    "cli_score",
    "session_index",
    "hour_of_day",
    "rolling_cli_mean",
]

# ==============================
# MODEL PARAMETERS
# ==============================
XGB_PARAMS = {
    "n_estimators": 200,
    "max_depth": 5,
    "learning_rate": 0.1,
    "random_state": 42,
}

# ==============================
# TRAIN TEST SPLIT
# ==============================
TEST_SIZE = 0.2
RANDOM_STATE = 42