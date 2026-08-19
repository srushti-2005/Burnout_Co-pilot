# src/data/supabase_manager.py
"""
Reads/writes behavioural session data using Supabase (Postgres).

Replaces: src/data/firestore_manager.py
Function names and shapes match the old module exactly, so app.py,
burnout_widget.py, and startup_logger.py only need their import line
changed:

    OLD: from src.data.firestore_manager import get_user_sessions, save_session
    NEW: from src.data.supabase_manager  import get_user_sessions, save_session
"""

from datetime import datetime, timezone
import logging
import pandas as pd
from src.auth.supabase_client import get_service_client
from src.cli_logic import (
    get_training_weights, get_training_bounds,
    normalize_with_fixed_bounds, calculate_cli, categorize_cli,
)

# Uses the SAME logger name as tracker.py ("burnout_tracker") so both
# modules' messages land in the same place. When startup_logger.py is
# the entrypoint (Task Scheduler / headless), it configures logging to
# write to startup_logger.log AND stdout at module load time — since
# Python child loggers propagate to that config automatically, these
# messages get captured there too, instead of vanishing the way a bare
# print() would under pythonw.exe (no console attached).
log = logging.getLogger("burnout_tracker")


def _compute_cli_for_row(row: dict) -> tuple:
    """
    Computes the canonical CLI + risk level for one raw session, using
    the SAME fixed training weights/bounds as the dashboard — so the
    value stored here always matches what app.py would compute live.
    This is what makes cli_score/risk_level meaningful to query
    directly in SQL (e.g. "show me all High-risk sessions") instead of
    always being NULL.
    """
    single = pd.DataFrame([{
        "typing_mean":     row["typing_mean"],
        "typing_variance": row["typing_variance"],
        "task_switching":  row["task_switching"],
        "work_duration":   row["work_duration"],
        "late_night":      int(bool(row["late_night"])),
    }])
    norm = normalize_with_fixed_bounds(single, get_training_bounds())
    cli = calculate_cli(norm.iloc[0], get_training_weights())
    return cli, categorize_cli(cli)


def save_session(uid: str, data: dict):
    """
    Inserts one behavioural session row for the given user, then updates
    their rolling personal baseline (see _update_baseline_after_session
    below). This is the ONE place session data enters the system, so
    every caller — tracker.py, burnout_widget.py, a future API — gets
    baseline tracking for free just by calling save_session().

    `data` keys expected (same as the old Firestore payload):
        typing_mean, typing_variance, task_switching,
        work_duration, late_night, hour_of_day (ignored — DB
        stores created_at automatically and hour_of_day is
        derived from it on read)
    """
    sb = get_service_client()
    row = {
        "user_id":         uid,
        "typing_mean":     float(data.get("typing_mean", 0)),
        "typing_variance": float(data.get("typing_variance", 0)),
        "task_switching":  int(data.get("task_switching", 0)),
        "work_duration":   float(data.get("work_duration", 0)),
        "late_night":      bool(data.get("late_night", 0)),
    }

    # Compute the canonical CLI at write time, using the same fixed
    # weights/bounds the dashboard uses at read time — so this column
    # is never NULL and always agrees with what the dashboard shows.
    try:
        cli, risk = _compute_cli_for_row(row)
        row["cli_score"]  = cli
        row["risk_level"] = risk
    except Exception as e:
        log.error(f"[supabase_manager] CLI computation failed at write time (non-fatal): {e}")

    result = sb.table("sessions").insert(row).execute()
    _update_baseline_after_session(sb, uid, row)
    return result


def get_user_sessions(uid: str, limit: int = 200) -> list[dict]:
    """
    Returns the user's most recent `limit` sessions, ordered oldest → newest
    (same order app.py expects when it does df.sort_values("timestamp")).

    Each dict is shaped like the old Firestore documents so app.py's
    downstream code (normalize_features, calculate_cli, etc.) needs
    zero changes:
        uid, typing_mean, typing_variance, task_switching,
        work_duration, late_night, hour_of_day, timestamp
    """
    sb = get_service_client()
    res = (
        sb.table("sessions")
        .select("*")
        .eq("user_id", uid)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = res.data or []
    rows.reverse()  # oldest -> newest

    sessions = []
    for r in rows:
        created = r.get("created_at")
        if created:
            # Supabase always stores/returns UTC, e.g. "2026-08-10T07:35:47+00:00".
            # That's correct — timestamptz should be UTC in the database.
            # The bug was downstream: nothing converted it to local time
            # before displaying it. .astimezone() with no args converts
            # to whatever timezone this machine (running Streamlit) is
            # set to — e.g. IST if the machine is in India.
            ts_utc = datetime.fromisoformat(created.replace("Z", "+00:00"))
            ts = ts_utc.astimezone()
        else:
            ts = datetime.now().astimezone()

        sessions.append({
            "uid":              r.get("user_id"),
            "typing_mean":      r.get("typing_mean", 0),
            "typing_variance":  r.get("typing_variance", 0),
            "task_switching":   r.get("task_switching", 0),
            "work_duration":    r.get("work_duration", 0),
            "late_night":       int(bool(r.get("late_night", False))),
            "hour_of_day":      ts.hour,
            "timestamp":        ts,
        })
    return sessions


def get_or_create_baseline(uid: str) -> dict:
    """
    New helper for the Personalization Layer (Section 4.1 #8 in your report).
    Returns the user's stored baseline row, or an empty dict if none yet.
    """
    sb = get_service_client()
    res = sb.table("user_baselines").select("*").eq("user_id", uid).execute()
    return res.data[0] if res.data else {}


def update_baseline(uid: str, baseline: dict):
    """Upserts the user's rolling behavioural baseline directly (manual use)."""
    sb = get_service_client()
    row = {"user_id": uid, **baseline}
    return sb.table("user_baselines").upsert(row).execute()


def _incremental_mean(old_avg, old_count: int, new_value: float) -> float:
    """Running average: new_avg = (old_avg * n + new_value) / (n + 1)."""
    if old_avg is None or not old_count:
        return float(new_value)
    return (float(old_avg) * old_count + float(new_value)) / (old_count + 1)


def _update_baseline_after_session(sb, uid: str, row: dict):
    """
    Updates the user's own rolling average for each raw behavioural
    feature. This is the mechanism behind Figure 4.4's "X% below your
    usual level" comparisons — it is DELIBERATELY separate from CLI
    computation (which always uses the fixed training weights/bounds
    from cli_logic.get_training_weights / get_training_bounds).
    Non-fatal if it fails — a missed baseline update should never block
    a session save.
    """
    try:
        existing = sb.table("user_baselines").select("*").eq("user_id", uid).execute()
        base  = existing.data[0] if existing.data else {}
        count = base.get("session_count", 0) or 0

        updated = {
            "user_id":             uid,
            "typing_mean_avg":     _incremental_mean(base.get("typing_mean_avg"),     count, row["typing_mean"]),
            "typing_variance_avg": _incremental_mean(base.get("typing_variance_avg"), count, row["typing_variance"]),
            "task_switching_avg":  _incremental_mean(base.get("task_switching_avg"),  count, row["task_switching"]),
            "work_duration_avg":   _incremental_mean(base.get("work_duration_avg"),   count, row["work_duration"]),
            "session_count":       count + 1,
        }
        sb.table("user_baselines").upsert(updated).execute()
    except Exception as e:
        log.error(f"[supabase_manager] baseline update failed (non-fatal): {e}")


def compare_to_baseline(uid: str, latest_session: dict) -> dict:
    """
    Compares one session's raw values against the user's own rolling
    baseline. Returns % above/below their usual level per feature —
    exactly the numbers Figure 4.4 ("Key Drivers") displays. Returns an
    empty dict if the user has no baseline yet (first-ever session).
    """
    base = get_or_create_baseline(uid)
    if not base or not base.get("session_count"):
        return {}

    def _pct_diff(current, avg):
        if not avg:
            return 0.0
        return round(((current - avg) / avg) * 100, 1)

    return {
        "typing_mean_vs_usual":     _pct_diff(latest_session.get("typing_mean", 0),     base.get("typing_mean_avg")),
        "typing_variance_vs_usual": _pct_diff(latest_session.get("typing_variance", 0), base.get("typing_variance_avg")),
        "task_switching_vs_usual":  _pct_diff(latest_session.get("task_switching", 0),  base.get("task_switching_avg")),
        "work_duration_vs_usual":   _pct_diff(latest_session.get("work_duration", 0),   base.get("work_duration_avg")),
    }
