"""
Wraps your real src/cli_logic.py instead of reimplementing it — this
guarantees FastAPI produces IDENTICAL CLI scores to your Streamlit
dashboard for the same input, since both call the same functions.
cli_logic.py handles its own weight/bounds caching internally
(_WEIGHTS_CACHE, _BOUNDS_CACHE) — no separate cache file needed here.
"""
import sys
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # burnout-project root
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cli_logic import (
    get_training_weights,
    get_training_bounds,
    normalize_with_fixed_bounds,
    calculate_cli,
    categorize_cli,
)

FEATURES = ["typing_mean", "typing_variance", "task_switching", "work_duration", "late_night"]


def compute_cli_score(signals: dict) -> tuple[float, str]:
    weights = get_training_weights()
    bounds = get_training_bounds()
    row = pd.DataFrame([signals])
    row_norm = normalize_with_fixed_bounds(row, bounds).iloc[0]
    cli = calculate_cli(row_norm, weights)
    category = categorize_cli(cli)
    return cli, category.lower()