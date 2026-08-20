import os
import pandas as pd
import numpy as np


# -----------------------------
# Resolve the training dataset path RELATIVE TO THIS FILE, not the
# process's current working directory.
#
# WHY THIS MATTERS: the old default path "data/raw/burnout_dataset.csv"
# is a relative path, which pandas resolves against os.getcwd(). That
# works fine when Streamlit is launched from the project folder — its
# cwd IS the project folder. But when Windows Task Scheduler launches
# startup_logger.py at logon, its working directory is NOT guaranteed
# to be your project folder (often defaults to something like
# System32). That silently breaks load_data() -> FileNotFoundError ->
# caught by the try/except in supabase_manager.save_session() ->
# cli_score/risk_level end up NULL for whichever process happened to
# be launched with the "wrong" cwd. This anchors the path to
# cli_logic.py's own location instead, so it resolves correctly no
# matter what launched the process (Streamlit, VS Code, Command
# Prompt, or Task Scheduler).
# -----------------------------
_THIS_DIR          = os.path.dirname(os.path.abspath(__file__))   # .../src
_PROJECT_ROOT       = os.path.dirname(_THIS_DIR)                   # project root
DEFAULT_DATA_PATH  = os.path.join(_PROJECT_ROOT, "data", "raw", "burnout_dataset.csv")


# -----------------------------
# Load Dataset
# -----------------------------
def load_data(path=DEFAULT_DATA_PATH):
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(["user_id", "timestamp"])
    return df


# -----------------------------
# Min-Max Scaling Function
# -----------------------------
def min_max_scale(series):
    """Safe min-max scale. Returns a Series of 0s if all values are identical."""
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(0.0, index=series.index)   # ← must be Series, not scalar
    return (series - mn) / (mx - mn)


# -----------------------------
# Normalize Selected Features
# -----------------------------
def normalize_features(df):
    df = df.copy()
    df["typing_mean_norm"]     = min_max_scale(df["typing_mean"])
    df["typing_variance_norm"] = min_max_scale(df["typing_variance"])
    df["task_switching_norm"]  = min_max_scale(df["task_switching"])
    df["work_duration_norm"]   = min_max_scale(df["work_duration"])
    return df


# -----------------------------
# CRITIC WEIGHT CALCULATION
# -----------------------------
def compute_critic_weights(df):
    """
    CRITIC method: weights based on standard deviation × information content
    (sum of (1 - |correlation|) for each feature pair).
    Falls back to equal weights when there is no variance in the data.
    """
    cols = [
        "typing_mean_norm",
        "typing_variance_norm",
        "task_switching_norm",
        "work_duration_norm",
        "late_night",
    ]

    # Guard: if any column is missing, fall back to equal weights
    missing = [c for c in cols if c not in df.columns]
    if missing:
        return {col: 1 / len(cols) for col in cols}

    data = df[cols].copy().astype(float)

    std_dev = data.std(ddof=1)   # sample std
    corr    = data.corr()

    # Replace NaN correlations (constant columns) with 0 so they don't break things
    corr = corr.fillna(0)

    C = {}
    for col in cols:
        info = sum(1 - abs(corr.loc[col, other]) for other in cols)
        C[col] = std_dev[col] * info

    total = sum(C.values())

    if total == 0 or pd.isna(total):
        return {col: 1 / len(cols) for col in cols}

    weights = {k: C[k] / total for k in C}

    # Ensure no weight is NaN (can happen if std is NaN for a column)
    weights = {k: (v if not pd.isna(v) else 1 / len(cols)) for k, v in weights.items()}

    return weights


# -----------------------------
# Fixed / Canonical Training Weights
# -----------------------------
_WEIGHTS_CACHE = {}


def get_training_weights(path=DEFAULT_DATA_PATH):
    """
    Returns the CRITIC-derived feature weights computed ONCE from the full
    training dataset, and caches them for the lifetime of the process.

    Why this exists: compute_critic_weights() is sensitive to the sample
    it's given — std devs and correlations shift with sample size, so
    recomputing weights on whatever small slice of live sessions a caller
    happens to have (e.g. one user's last 100 sessions) produces different
    weights on every call. That's not reproducible and can't be defended
    under questioning.

    Every scoring surface (dashboard, widget, future API) should call this
    instead of compute_critic_weights() directly for live inference, so the
    same fixed, dataset-derived weights are used everywhere. Weights are
    only ever recomputed if the underlying training dataset changes.
    """
    if path not in _WEIGHTS_CACHE:
        df = load_data(path)
        df = normalize_features(df)
        _WEIGHTS_CACHE[path] = compute_critic_weights(df)
    return _WEIGHTS_CACHE[path]


# -----------------------------
# Fixed / Canonical Training Bounds (for live normalization)
# -----------------------------
_BOUNDS_CACHE = {}


def get_training_bounds(path=DEFAULT_DATA_PATH):
    """
    Returns the min/max of each raw behavioural feature from the FULL
    training dataset — the same fixed reference frame used to derive
    the CRITIC weights (get_training_weights) and train the GBT model.

    Why this exists: normalize_features() min-max scales relative to
    whatever DataFrame it's given. That's correct for the one-time
    training pipeline (load_and_process), which is meant to DEFINE the
    reference distribution (see Table 3.1 in the report). But if the
    same function is reused live — e.g. on a single user's own ~100
    sessions via the widget or dashboard — the min/max come from that
    small slice instead, so the exact same raw session produces a
    DIFFERENT normalized value (and therefore a different CLI)
    depending on who else happens to be in the batch. That silently
    breaks the same reproducibility get_training_weights() was built
    to fix — it just doesn't crash, so it's easy to miss.

    Every live scoring surface (dashboard, widget, future API) should
    normalize against these fixed bounds via normalize_with_fixed_bounds()
    below, instead of calling normalize_features() directly.
    """
    if path not in _BOUNDS_CACHE:
        df = load_data(path)
        _BOUNDS_CACHE[path] = {
            "typing_mean":     (float(df["typing_mean"].min()),     float(df["typing_mean"].max())),
            "typing_variance": (float(df["typing_variance"].min()), float(df["typing_variance"].max())),
            "task_switching":  (float(df["task_switching"].min()),  float(df["task_switching"].max())),
            "work_duration":   (float(df["work_duration"].min()),   float(df["work_duration"].max())),
        }
    return _BOUNDS_CACHE[path]


def normalize_with_fixed_bounds(df, bounds=None):
    """
    Same output columns as normalize_features() (typing_mean_norm, etc.)
    but scales every value against FIXED training-dataset bounds instead
    of the local DataFrame's own min/max. Use this — not
    normalize_features() — for any LIVE CLI computation (dashboard,
    widget, API), so scores stay comparable to what the CRITIC weights
    and GBT model were calibrated against.

    Live values outside the training range are clipped to [0, 1] rather
    than extrapolated (e.g. a session with more task-switching than any
    training example just scores a full 1.0 on that feature, instead of
    a nonsensical value >1).
    """
    if bounds is None:
        bounds = get_training_bounds()
    df = df.copy()

    def _scale(series, mn, mx):
        if mx == mn:
            return pd.Series(0.0, index=series.index)
        return ((series - mn) / (mx - mn)).clip(0.0, 1.0)

    df["typing_mean_norm"]     = _scale(df["typing_mean"],     *bounds["typing_mean"])
    df["typing_variance_norm"] = _scale(df["typing_variance"], *bounds["typing_variance"])
    df["task_switching_norm"]  = _scale(df["task_switching"],  *bounds["task_switching"])
    df["work_duration_norm"]   = _scale(df["work_duration"],   *bounds["work_duration"])
    return df


# -----------------------------
# Calculate CLI
# -----------------------------
def calculate_cli(row, weights):
    cli = (
        weights["typing_mean_norm"]     * row["typing_mean_norm"]     +
        weights["typing_variance_norm"] * row["typing_variance_norm"] +
        weights["task_switching_norm"]  * row["task_switching_norm"]  +
        weights["work_duration_norm"]   * row["work_duration_norm"]   +
        weights["late_night"]           * row["late_night"]
    )
    return round(float(cli), 3)


# -----------------------------
# Categorize CLI
# -----------------------------
def categorize_cli(cli):
    if cli < 0.4:
        return "Low"
    elif cli < 0.7:
        return "Medium"
    else:
        return "High"


# -----------------------------
# Add CLI to DataFrame
# -----------------------------
def add_cli(df):
    df      = df.copy()
    weights = compute_critic_weights(df)
    df["CLI"]          = df.apply(lambda row: calculate_cli(row, weights), axis=1)
    df["CLI_category"] = df["CLI"].apply(categorize_cli)
    return df


# -----------------------------
# Master Pipeline
# -----------------------------
def load_and_process(path=DEFAULT_DATA_PATH):
    df = load_data(path)
    df = normalize_features(df)
    df = add_cli(df)
    return df


# -----------------------------
# Simulation Engine
# -----------------------------
def simulate_scenario(input_data, path=DEFAULT_DATA_PATH):
    """
    Calculates CLI for a single hypothetical set of inputs,
    scaled against the real dataset distribution.

    input_data example:
        {
            "typing_mean": 70,
            "typing_variance": 20,
            "task_switching": 45,
            "work_duration": 10,
            "late_night": 1
        }
    """
    df = load_data(path)
    df = normalize_features(df)

    weights = compute_critic_weights(df)

    def scale(value, column):
        mn, mx = df[column].min(), df[column].max()
        if mx == mn:
            return 0.0
        return (value - mn) / (mx - mn)

    typing_mean_norm     = scale(input_data["typing_mean"],     "typing_mean")
    typing_variance_norm = scale(input_data["typing_variance"], "typing_variance")
    task_switching_norm  = scale(input_data["task_switching"],  "task_switching")
    work_duration_norm   = scale(input_data["work_duration"],   "work_duration")

    cli = (
        weights["typing_mean_norm"]     * typing_mean_norm     +
        weights["typing_variance_norm"] * typing_variance_norm +
        weights["task_switching_norm"]  * task_switching_norm  +
        weights["work_duration_norm"]   * work_duration_norm   +
        weights["late_night"]           * input_data["late_night"]
    )

    cli = round(float(cli), 3)
    return cli, categorize_cli(cli)
