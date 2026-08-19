import logging
from fastapi import APIRouter, Depends, HTTPException

from core.security import get_current_user_id
from core.supabase_client import get_service_client
from core.config import SESSIONS_TABLE
from schemas.schemas import PredictRequest, PredictResponse
from services.cli import compute_cli_score
from services.predictor import predict_risk

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("", response_model=PredictResponse)
def predict(payload: PredictRequest, user_id: str = Depends(get_current_user_id)):
    if payload.session_id:
        try:
            client = get_service_client()
            result = (
                client.table(SESSIONS_TABLE).select("*")
                .eq("id", payload.session_id).eq("user_id", user_id)
                .single().execute()
            )
        except Exception:
            logger.exception("Failed to fetch session %s", payload.session_id)
            raise HTTPException(status_code=404, detail="Session not found")
        row = result.data
        signals = {
            "typing_mean": row["typing_mean"], "typing_variance": row["typing_variance"],
            "task_switching": row["task_switching"], "work_duration": row["work_duration"],
            "late_night": int(row["late_night"]),
        }
    else:
        signals = {
            "typing_mean": payload.typing_mean, "typing_variance": payload.typing_variance,
            "task_switching": payload.task_switching, "work_duration": payload.work_duration,
            "late_night": payload.late_night,
        }
        if any(v is None for v in signals.values()):
            raise HTTPException(status_code=422, detail="Provide session_id or all raw fields")

    cli_score, risk_level = compute_cli_score(signals)
    try:
        model_out = predict_risk(user_id, signals)
    except Exception:
        logger.exception("Model prediction failed for user %s", user_id)
        raise HTTPException(status_code=500, detail="Prediction failed, please try again")

    return PredictResponse(
        cli_score=cli_score, risk_level=risk_level,
        risk_probability=model_out["risk_probability"],
        shap_explanation=model_out["shap_explanation"],
    )