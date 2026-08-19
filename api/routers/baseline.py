import logging
import sys
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException

from core.security import get_current_user_id
from schemas.schemas import BaselineResponse

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.data.supabase_manager import get_or_create_baseline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/baseline", tags=["baseline"])


@router.get("", response_model=BaselineResponse)
def get_baseline(user_id: str = Depends(get_current_user_id)):
    try:
        base = get_or_create_baseline(user_id)
    except Exception:
        logger.exception("Failed to fetch baseline for user %s", user_id)
        raise HTTPException(status_code=502, detail="Could not load baseline, please try again")

    if not base:
        raise HTTPException(status_code=404, detail="Not enough session history yet")

    return BaselineResponse(user_id=user_id, **{
        k: base.get(k, 0) for k in
        ["typing_mean_avg", "typing_variance_avg", "task_switching_avg", "work_duration_avg", "session_count"]
    })