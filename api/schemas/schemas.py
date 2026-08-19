from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SessionIn(BaseModel):
    typing_mean: float
    typing_variance: float
    task_switching: float
    work_duration: float
    late_night: int = Field(..., ge=0, le=1)
    timestamp_utc: Optional[datetime] = None


class SessionOut(BaseModel):
    id: str
    user_id: str
    typing_mean: float
    typing_variance: float
    task_switching: float
    work_duration: float
    late_night: int
    cli_score: float
    risk_level: str
    timestamp_utc: datetime


class PredictRequest(BaseModel):
    session_id: Optional[str] = None
    typing_mean: Optional[float] = None
    typing_variance: Optional[float] = None
    task_switching: Optional[float] = None
    work_duration: Optional[float] = None
    late_night: Optional[int] = None


class PredictResponse(BaseModel):
    cli_score: float
    risk_level: str
    risk_probability: float
    shap_explanation: dict


class BaselineResponse(BaseModel):
    user_id: str
    typing_mean_avg: float = 0
    typing_variance_avg: float = 0
    task_switching_avg: float = 0
    work_duration_avg: float = 0
    session_count: int = 0


class SuggestionsResponse(BaseModel):
    risk_level: str
    suggestions: list[str]