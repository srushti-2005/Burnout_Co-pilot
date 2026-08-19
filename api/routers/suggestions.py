from fastapi import APIRouter
from services.suggestions import get_suggestions_for_session
from services.cli import compute_cli_score
from schemas.schemas import SessionIn, SuggestionsResponse

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


@router.post("", response_model=SuggestionsResponse)
def suggestions(payload: SessionIn):
    signals = {
        "typing_mean": payload.typing_mean, "typing_variance": payload.typing_variance,
        "task_switching": payload.task_switching, "work_duration": payload.work_duration,
        "late_night": payload.late_night,
    }
    cli, risk_level = compute_cli_score(signals)
    texts = get_suggestions_for_session(cli=cli, **signals)
    return SuggestionsResponse(risk_level=risk_level, suggestions=texts)