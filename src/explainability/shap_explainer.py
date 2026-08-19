# src/explainability/shap_explainer.py

import shap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os

from src.config.config import OUTPUT_DIR


# ═══════════════════════════════════════════════════════════════════════════════
# P2's ORIGINAL CODE — DO NOT MODIFY
# ═══════════════════════════════════════════════════════════════════════════════

def generate_shap_plots(model, X):

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Use a smaller sample for faster SHAP computation
    X_sample = X.sample(min(200, len(X)), random_state=42)

    # Create SHAP explainer
    explainer = shap.TreeExplainer(model)

    # Compute SHAP values
    shap_values = explainer.shap_values(X_sample)

    # -----------------------------
    # Global Feature Importance Plot
    # -----------------------------
    plt.figure()

    shap.summary_plot(
        shap_values,
        X_sample,
        show=False
    )

    plt.savefig(
        os.path.join(OUTPUT_DIR, "shap_summary.png"),
        bbox_inches="tight"
    )

    plt.close()

    # -----------------------------
    # Single Prediction Explanation
    # -----------------------------
    plt.figure()

    shap.force_plot(
        explainer.expected_value,
        shap_values[0],
        X_sample.iloc[0],
        matplotlib=True,
        show=False
    )

    plt.savefig(
        os.path.join(OUTPUT_DIR, "shap_force_plot.png"),
        bbox_inches="tight"
    )

    plt.close()

    print("✅ SHAP plots generated!")
    print(f"Saved in: {OUTPUT_DIR}")


# ═══════════════════════════════════════════════════════════════════════════════
# P3 ADDITIONS — Real-time per-user explainability for the dashboard
# ═══════════════════════════════════════════════════════════════════════════════

# Exact feature columns from train_model.py — DO NOT change order
FEATURE_COLUMNS = [
    "typing_mean",
    "typing_variance",
    "task_switching",
    "work_duration",
    "late_night",
    "hour_of_day",
    "session_index",
]

# Human-readable labels for UI display
FEATURE_LABELS = {
    "typing_mean":      "Typing Speed",
    "typing_variance":  "Typing Variance",
    "task_switching":   "Task Switching",
    "work_duration":    "Work Duration",
    "late_night":       "Late Night Work",
    "hour_of_day":      "Hour of Day",
    "session_index":    "Session Index",
}


def get_user_shap_values(model, user_row: pd.DataFrame):
    """
    Computes real-time SHAP values for a single user row.

    Args:
        model    : loaded XGBClassifier from model.pkl
        user_row : pd.DataFrame — 1 row, only FEATURE_COLUMNS

    Returns:
        shap_vals      (np.ndarray) : 1D array, one SHAP value per feature
        expected_value (float)      : model base value (class 1 / burnout)
    """
    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(user_row)

    # XGBClassifier returns list [class_0_vals, class_1_vals]
    # Take class 1 = burnout positive class
    if isinstance(shap_values, list):
        sv = shap_values[1][0]
        ev = float(explainer.expected_value[1])
    else:
        sv = shap_values[0]
        ev = float(explainer.expected_value)

    return sv, ev


def get_user_baseline(df: pd.DataFrame, user_id: int):
    """
    Computes user baseline safely.

    FIXES:
    - Handles missing user_id
    - Handles index case
    - Prevents crash
    """

    # Ensure user_id exists
    if "user_id" not in df.columns:
        if df.index.name == "user_id":
            df = df.reset_index()
        else:
            raise ValueError(
                f"'user_id' column missing. Available: {list(df.columns)}"
            )

    available = [c for c in FEATURE_COLUMNS if c in df.columns]

    if not available:
        raise ValueError("No feature columns found in dataframe")

    user_data = df[df["user_id"] == user_id]

    if user_data.empty:
        raise ValueError(f"No data for user_id={user_id}")

    user_data = user_data[available]

    user_baseline = user_data.mean()
    pop_baseline  = df[available].mean()

    return user_baseline, pop_baseline


def build_natural_language_insights(
    shap_vals:     np.ndarray,
    user_row:      pd.DataFrame,
    user_baseline: pd.Series,
    pop_baseline:  pd.Series,
    top_n:         int = 3
) -> list:
    """
    Converts SHAP values into plain-English sentences for the user.

    Each insight explains:
      - Whether the feature is raising or lowering their burnout risk
      - How far today's value is from their own personal norm
      - How far today's value is from the average user

    Args:
        shap_vals     : from get_user_shap_values()
        user_row      : single-row DataFrame (FEATURE_COLUMNS only)
        user_baseline : from get_user_baseline()
        pop_baseline  : from get_user_baseline()
        top_n         : number of top drivers to return (default 3)

    Returns:
        List of (shap_val: float, insight_text: str) sorted by |SHAP| descending
    """
    available = [c for c in FEATURE_COLUMNS if c in user_row.columns]
    paired    = list(zip(available, shap_vals[:len(available)]))
    paired.sort(key=lambda x: abs(x[1]), reverse=True)

    insights = []

    for feat, shap_val in paired[:top_n]:

        label       = FEATURE_LABELS.get(feat, feat.replace("_", " ").title())
        current_val = float(user_row[feat].values[0])
        u_norm      = float(user_baseline.get(feat, 0))
        p_norm      = float(pop_baseline.get(feat, 0))
        direction   = "increasing" if shap_val > 0 else "decreasing"
        arrow       = "↑" if shap_val > 0 else "↓"

        # Personal baseline deviation
        self_note = ""
        if u_norm != 0:
            pct = ((current_val - u_norm) / abs(u_norm)) * 100
            if abs(pct) > 5:
                word      = "above" if pct > 0 else "below"
                self_note = f"{abs(pct):.0f}% {word} your usual level"

        # Population baseline deviation
        pop_note = ""
        if p_norm != 0:
            pct = ((current_val - p_norm) / abs(p_norm)) * 100
            if abs(pct) > 5:
                word     = "above" if pct > 0 else "below"
                pop_note = f"{abs(pct):.0f}% {word} average user"

        # Assemble sentence
        text = f"{arrow} **{label}** is {direction} your burnout risk"
        if self_note and pop_note:
            text += f" — {self_note} and {pop_note}"
        elif self_note:
            text += f" — {self_note}"
        elif pop_note:
            text += f" — {pop_note}"
        text += "."

        insights.append((float(shap_val), text))

    return insights


def plot_waterfall_chart(
    shap_vals:      np.ndarray,
    expected_value: float,
    user_row:       pd.DataFrame,
    max_display:    int = 7
) -> plt.Figure:
    """
    Renders a SHAP waterfall chart styled to match the dark dashboard theme.
    Returns a matplotlib Figure → pass directly to st.pyplot() in app.py.

    Args:
        shap_vals      : from get_user_shap_values()
        expected_value : from get_user_shap_values()
        user_row       : single-row DataFrame (FEATURE_COLUMNS only)
        max_display    : max features shown (default 7 = all features)

    Returns:
        matplotlib Figure
    """
    available    = [c for c in FEATURE_COLUMNS if c in user_row.columns]
    labels       = [FEATURE_LABELS.get(f, f) for f in available]
    feature_vals = user_row[available].values[0]

    explanation = shap.Explanation(
        values        = shap_vals[:len(available)],
        base_values   = expected_value,
        data          = feature_vals,
        feature_names = labels
    )

    plt.close("all")
    shap.plots.waterfall(explanation, max_display=max_display, show=False)

    fig = plt.gcf()

    # Restyle to match dark dashboard
    bg = "#0f1117"
    fig.patch.set_facecolor(bg)
    for ax in fig.get_axes():
        ax.set_facecolor(bg)
        ax.tick_params(colors="#cccccc", labelsize=9)
        ax.xaxis.label.set_color("#cccccc")
        ax.yaxis.label.set_color("#cccccc")
        for spine in ax.spines.values():
            spine.set_color("#444444")

    for txt in fig.findobj(plt.Text):
        txt.set_color("#e0e0e0")

    plt.tight_layout()
    return fig


def build_baseline_table(
    user_row:      pd.DataFrame,
    user_baseline: pd.Series,
    pop_baseline:  pd.Series
) -> pd.DataFrame:
    """
    Builds the comparison table: Today vs Your Norm vs Avg User.
    Arrow indicators: ⬆ above  ⬇ below  ➡ similar (within 5%)

    Returns:
        pd.DataFrame ready to pass into st.dataframe()
    """
    available = [c for c in FEATURE_COLUMNS if c in user_row.columns]
    rows = []

    def arrow(val, ref):
        if ref == 0:
            return "➡"
        diff_pct = ((val - ref) / abs(ref)) * 100
        if   diff_pct >  5: return "⬆"
        elif diff_pct < -5: return "⬇"
        else:               return "➡"

    for feat in available:
        curr   = round(float(user_row[feat].values[0]), 2)
        u_norm = round(float(user_baseline.get(feat, 0)), 2)
        p_norm = round(float(pop_baseline.get(feat, 0)),  2)

        rows.append({
            "Feature":       FEATURE_LABELS.get(feat, feat),
            "Today":         curr,
            "Your Baseline": f"{u_norm}  {arrow(curr, u_norm)}",
            "Avg User":      f"{p_norm}  {arrow(curr, p_norm)}",
        })

    return pd.DataFrame(rows)