"""
Real-time behavioural data logger using pynput + psutil.

Runs silently in the background after user login.
Collects data over a 1-hour window, then saves one session
row to Supabase and resets all counters for the next hour.

Metrics collected:
  typing_mean      — average keystrokes per minute over the hour
  typing_variance  — variance in per-minute keystroke counts
  task_switching   — number of unique app/window switches in the hour
  work_duration    — cumulative hours the tracker has been running
  late_night       — 1 if the hour of save time is >= 22 or <= 5
  hour_of_day      — hour (0-23) at the moment of saving

Architecture:
  Thread-1  _keyboard_listener   — pynput, records every keypress timestamp
  Thread-2  _window_poller       — polls active window title every 3 s
  Thread-3  _collection_loop     — wakes every INTERVAL_HOURS, computes + saves + resets
"""

import threading
import time
import logging
from datetime import datetime
from collections import deque

logging.basicConfig(
    level=logging.INFO,
    format="[PyLogger %(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("burnout_tracker")

# ── Optional dependency flags ─────────────────────────────────────────────────
try:
    from pynput import keyboard as _kb
    PYNPUT_OK = True
except Exception:
    PYNPUT_OK = False
    log.warning("pynput not available — typing metrics will be 0")

try:
    import psutil
    PSUTIL_OK = True
except Exception:
    PSUTIL_OK = False

try:
    import pygetwindow as _gw
    PYGETWINDOW_OK = True
except Exception:
    PYGETWINDOW_OK = False

# ── Constants ────────────────────────────────────────────────────────────────
INTERVAL_HOURS   = 0.02
INTERVAL_SECONDS = INTERVAL_HOURS * 3600
WINDOW_POLL_SEC  = 3

# ── Shared state (module-level, protected by locks) ──────────────────────────
_stop_event      = threading.Event()
_tracker_thread  = None
_kb_listener     = None
_win_thread      = None

_key_times : deque = deque()
_key_lock          = threading.Lock()

_last_window  = None
_switch_count = 0
_switch_lock  = threading.Lock()

# Tracks when this tracker session started (reset on start_tracker call)
_session_start: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# THREAD 1 — Keyboard listener
# ═══════════════════════════════════════════════════════════════════════════════

def _on_keypress(key):
    with _key_lock:
        _key_times.append(time.time())


# ═══════════════════════════════════════════════════════════════════════════════
# THREAD 2 — Active window poller
# ═══════════════════════════════════════════════════════════════════════════════

def _window_poller():
    global _last_window, _switch_count

    while not _stop_event.is_set():
        title = _get_active_window_title()
        if title:
            with _switch_lock:
                if title != _last_window:
                    if _last_window is not None:
                        _switch_count += 1
                        log.debug(f"Window switch → {title[:40]}")
                    _last_window = title

        _stop_event.wait(timeout=WINDOW_POLL_SEC)


def _get_active_window_title() -> str:
    if PYGETWINDOW_OK:
        try:
            win = _gw.getActiveWindow()
            return win.title.strip() if win and win.title else ""
        except Exception:
            pass

    if PSUTIL_OK:
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            pid  = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            proc = psutil.Process(pid.value)
            return proc.name()
        except Exception:
            pass

    return ""


# ═══════════════════════════════════════════════════════════════════════════════
# METRICS COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_typing_stats(interval_seconds: int) -> tuple:
    """Returns (mean_keystrokes_per_min, variance) for the current interval."""
    now    = time.time()
    cutoff = now - interval_seconds

    with _key_lock:
        while _key_times and _key_times[0] < cutoff:
            _key_times.popleft()
        times = list(_key_times)

    if not times:
        return 0.0, 0.0

    n_buckets   = max(1, interval_seconds // 60)
    bucket_size = interval_seconds / n_buckets
    buckets     = [0] * n_buckets

    for t in times:
        idx = min(int((t - cutoff) / bucket_size), n_buckets - 1)
        buckets[idx] += 1

    mean     = sum(buckets) / n_buckets
    variance = sum((b - mean) ** 2 for b in buckets) / n_buckets

    return round(mean, 2), round(variance, 2)


def _get_and_reset_switches() -> int:
    global _switch_count
    with _switch_lock:
        count         = _switch_count
        _switch_count = 0
    return count


def _reset_keystrokes():
    with _key_lock:
        _key_times.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# THREAD 3 — Collection loop
# ═══════════════════════════════════════════════════════════════════════════════

def _collection_loop(uid: str, session_start: float):
    """
    Saves one session to Supabase every INTERVAL_HOURS.
    work_duration is the total hours elapsed since tracker started.
    """
    # Import here to avoid circular imports at module load time
    from src.data.supabase_manager import save_session

    log.info(f"Collection loop started for uid={uid}. "
             f"First save in {INTERVAL_HOURS} hour(s).")

    while not _stop_event.is_set():

        # Sleep in 10-second chunks to remain responsive to stop signals
        elapsed_sleep = 0
        while elapsed_sleep < INTERVAL_SECONDS and not _stop_event.is_set():
            _stop_event.wait(timeout=10)
            elapsed_sleep += 10

        if _stop_event.is_set():
            break

        # ── Compute metrics ───────────────────────────────────────────────────
        now      = datetime.now()
        hour     = now.hour
        late     = 1 if (hour >= 22 or hour <= 5) else 0

        # work_duration = hours elapsed since this tracking session started
        duration = round((time.time() - session_start) / 3600, 2)

        typing_mean, typing_var = _compute_typing_stats(INTERVAL_SECONDS)
        switches                = _get_and_reset_switches()
        _reset_keystrokes()

        session_data = {
            "typing_mean":     typing_mean,
            "typing_variance": typing_var,
            "task_switching":  switches,
            "work_duration":   duration,
            "late_night":      late,
            "hour_of_day":     hour,
        }

        # ── Save to Supabase ──────────────────────────────────────────────────
        try:
            save_session(uid, session_data)
            log.info(
                f"✅ Session saved — "
                f"typing_mean={typing_mean} kpm | "
                f"typing_var={typing_var} | "
                f"switches={switches} | "
                f"work_duration={duration:.2f}h | "
                f"late_night={bool(late)} | "
                f"hour={hour}"
            )
        except Exception as e:
            log.error(f"❌ Failed to save session: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def start_tracker(uid: str):
    """
    Starts the real-time behavioural logger for the logged-in user.
    Safe to call multiple times — does nothing if already running.
    """
    global _tracker_thread, _kb_listener, _win_thread, _stop_event, _session_start

    if _tracker_thread and _tracker_thread.is_alive():
        log.info("Tracker already running — skipping start.")
        return

    # ── Reset state for a fresh session ──────────────────────────────────────
    _stop_event.clear()
    _session_start = time.time()

    with _key_lock:
        _key_times.clear()
    with _switch_lock:
        global _switch_count, _last_window
        _switch_count = 0
        _last_window  = None

    # ── Start keyboard listener ───────────────────────────────────────────────
    if PYNPUT_OK:
        try:
            _kb_listener = _kb.Listener(on_press=_on_keypress, daemon=True)
            _kb_listener.start()
            log.info("⌨️  Keyboard listener started")
        except Exception as e:
            log.warning(f"⌨️  Keyboard listener failed to start: {e}")
    else:
        log.warning("⌨️  pynput unavailable — install it for typing metrics")

    # ── Start window poller ───────────────────────────────────────────────────
    _win_thread = threading.Thread(
        target=_window_poller,
        name="burnout_window_poller",
        daemon=True,
    )
    _win_thread.start()
    log.info("🪟 Window poller started")

    # ── Start collection loop ─────────────────────────────────────────────────
    _tracker_thread = threading.Thread(
        target=_collection_loop,
        args=(uid, _session_start),
        name="burnout_collection_loop",
        daemon=True,
    )
    _tracker_thread.start()

    log.info(f"🚀 PyLogger started for uid={uid} — saving every {INTERVAL_HOURS} hour(s)")


def stop_tracker():
    """Stops all tracking threads and the keyboard listener gracefully."""
    global _kb_listener
    _stop_event.set()

    if _kb_listener:
        try:
            _kb_listener.stop()
        except Exception:
            pass
        _kb_listener = None

    log.info("🛑 PyLogger stopped.")


def is_running() -> bool:
    """Returns True if the collection loop thread is alive."""
    return _tracker_thread is not None and _tracker_thread.is_alive()


def get_current_stats() -> dict:
    """
    Live snapshot of the current interval's metrics — no save, no reset.
    """
    now = datetime.now()
    typing_m, typing_v = _compute_typing_stats(INTERVAL_SECONDS)
    with _switch_lock:
        switches = _switch_count

    elapsed_hours = round((time.time() - _session_start) / 3600, 2) if _session_start else 0.0

    return {
        "typing_mean":     typing_m,
        "typing_variance": typing_v,
        "task_switching":  switches,
        "work_duration":   elapsed_hours,
        "hour_of_day":     now.hour,
        "late_night":      1 if (now.hour >= 22 or now.hour <= 5) else 0,
    }