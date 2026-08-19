import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]

MODEL_PATH = BASE_DIR / "models" / "model.pkl"
TRAINING_DATA_PATH = BASE_DIR / "data" / "raw" / "burnout_dataset.csv"

SESSIONS_TABLE = "sessions"
BASELINES_TABLE = "user_baselines"

CORS_ORIGINS = ["*"]