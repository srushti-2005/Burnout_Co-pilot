"""
Loads the trained model and computes SHAP values, using the model's
ACTUAL expected features — confirmed directly by the model's own
error message: typing_mean, typing_variance, task_switching,
work_duration, late_night, hour_of_day, session_index. This matches
shap_explainer.py's FEATURE_COLUMNS, not config.py's — config.py's
9-feature list was stale/incorrect for this particular model.pkl.
"""
import sys
from pathlib import Path
from datetime import datetime, timezone
import joblib
import shap
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config.config import MODEL_PATH
from src.data.supabase_manager import get_user_sessions

FEATURES = ["typing_mean", "typing_variance", "task_switching", "work_duration", "late_night", "hour_of_day", "session_index"]

_model = None
_explainer = None


def _load():
    global _model, _explainer
    if _model is None:
        _model = joblib.load(MODEL_PATH)
        _explainer = shap.TreeExplainer(_model)
    return _model, _explainer


def _build_feature_row(user_id: str, signals: dict) -> dict:
    now = datetime.now(timezone.utc).astimezone()
    past_sessions = get_user_sessions(user_id, limit=1000)
    session_index = len(past_sessions)

    return {
        "typing_mean": signals["typing_mean"],
        "typing_variance": signals["typing_variance"],
        "task_switching": signals["task_switching"],
        "work_duration": signals["work_duration"],
        "late_night": signals["late_night"],
        "hour_of_day": now.hour,
        "session_index": session_index,
    }


def predict_risk(user_id: str, signals: dict) -> dict:
    model, explainer = _load()
    row = _build_feature_row(user_id, signals)
    x_df = pd.DataFrame([row])[FEATURES]

    proba = model.predict_proba(x_df)[0]
    risk_probability = float(proba[1]) if len(proba) > 1 else float(proba[0])

    shap_values = explainer.shap_values(x_df)
    values = shap_values[1][0] if isinstance(shap_values, list) else shap_values[0]
    shap_explanation = {f: round(float(v), 4) for f, v in zip(FEATURES, values)}

    return {
        "risk_probability": round(risk_probability, 4),
        "shap_explanation": shap_explanation,
    }