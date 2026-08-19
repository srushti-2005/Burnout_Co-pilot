# burnout_widget.py
"""
Burnout Co-pilot — Safe Desktop Widget
----------------------------------------
SAFE VERSION — No keyboard hooks, no low-level system access.

Tracks safely using only:
  - psutil  : CPU usage, process count
  - datetime: work duration, hour of day
  - Firestore: real session data when signed in

Button behaviour:
  ×  = hides widget to system tray  (logging + saving CONTINUES)
  −  = shrinks to compact 40px bar, stays on screen
  □  = restores full widget from compact bar (click − again)

Tray icon menu:
  Show Widget   → brings hidden widget back to screen
  Open Web App  → opens localhost:8501 in browser
  Quit          → ONLY way to fully stop widget and logging

Always-visible:
  Uses Win32 SetWindowPos (HWND_TOPMOST) in a background loop every
  2 s so the widget is never buried behind other windows — even after
  unlocking the desktop, full-screen apps, or UAC prompts.

Startup:
  --register-startup writes a .vbs silent launcher so the widget
  appears as a visible window (not a hidden pythonw.exe process).
  Re-run --register-startup any time you move the project folder.

Saves stats to Firestore every 1 hour.
Refreshes display every 60 seconds.

SETUP:
    pip install psutil pystray pillow
    python burnout_widget.py
    python burnout_widget.py --register-startup   (run as Admin)
"""

import sys
import json
import time
import threading
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import tkinter as tk
except ImportError:
    print("tkinter not found. Reinstall Python with tcl/tk option.")
    sys.exit(1)

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_OK = True
except ImportError:
    TRAY_OK = False
    print("[Widget] pystray/pillow not found — tray icon disabled. "
          "Install with: pip install pystray pillow")

# Win32 always-on-top support (Windows only, silently skipped on other OS)
try:
    import ctypes
    _user32         = ctypes.windll.user32
    _HWND_TOPMOST   = -1       # always above all normal windows
    _SWP_NOMOVE     = 0x0002
    _SWP_NOSIZE     = 0x0001
    _SWP_NOACTIVATE = 0x0010   # do NOT steal keyboard focus
    _SWP_FLAGS      = _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE
    WIN32_OK        = True
except Exception:
    WIN32_OK = False

CREDS_FILE  = PROJECT_ROOT / ".burnout_local_creds.json"
REFRESH_MS  = 60_000
SAVE_MS     = 3_600_000
WEB_APP_URL = "http://localhost:8501"

BG       = "#1e1f2e"
BG2      = "#272838"
ACCENT   = "#a8a4ff"
TEXT     = "#e8e8f4"
MUTED    = "#6b6d8a"
BORDER   = "#3a3b54"
TITLEBAR = "#16172a"
LOW_C    = "#00c48c"
MID_C    = "#ffaa00"
HIGH_C   = "#ff5370"

RISK_COLOR = {"Low": LOW_C, "Medium": MID_C, "High": HIGH_C}
RISK_LABEL = {"Low": "LOW RISK", "Medium": "MED RISK", "High": "HIGH RISK"}

_t0 = time.time()


# ─────────────────────────── credentials ────────────────────────────

def load_credentials():
    try:
        if CREDS_FILE.exists():
            d = json.loads(CREDS_FILE.read_text())
            if "uid" in d and "email" in d:
                return d
    except Exception:
        pass
    return None


# ─────────────────────────── stats / data ───────────────────────────

def get_safe_stats():
    now         = datetime.now()
    elapsed_hrs = round((time.time() - _t0) / 3600, 2)
    hour        = now.hour
    late        = 1 if hour >= 22 or hour <= 5 else 0

    cpu = 0.0
    proc_count = 0
    if PSUTIL_OK:
        try:
            cpu        = psutil.cpu_percent(interval=0.5)
            proc_count = len(psutil.pids())
        except Exception:
            pass

    def _scale(v, mn, mx):
        return 0.0 if mx == mn else max(0.0, min(1.0, (v - mn) / (mx - mn)))

    local_cli = round(
        0.25 * _scale(cpu,         0,  100) +
        0.20 * _scale(elapsed_hrs, 0,   12) +
        0.10 * _scale(proc_count,  50, 400) +
        0.30 * late, 3
    )
    local_cli = min(local_cli, 1.0)
    cat = "High" if local_cli >= 0.7 else "Medium" if local_cli >= 0.4 else "Low"

    return {
        "time":      now.strftime("%H:%M"),
        "hour":      hour,
        "late":      late,
        "cpu":       round(cpu, 1),
        "proc":      proc_count,
        "duration":  elapsed_hrs,
        "local_cli": local_cli,
        "local_cat": cat,
    }


_fb_ready = False

def _init_fb():
    global _fb_ready
    if _fb_ready:
        return True
    try:
        from src.auth.supabase_client import init_supabase
        init_supabase()
        _fb_ready = True
        return True
    except Exception:
        return False


def fetch_firestore_stats(uid):
    try:
        if not _init_fb():
            return None
        from src.data.supabase_manager import get_user_sessions
        from src.cli_logic import (
            normalize_with_fixed_bounds, calculate_cli, categorize_cli,
            get_training_weights, get_training_bounds,
        )
        import pandas as pd

        sessions = get_user_sessions(uid, limit=100)
        if not sessions:
            return {"no_data": True}

        df = pd.DataFrame(sessions)
        for col in ["typing_mean", "typing_variance", "task_switching",
                    "work_duration", "late_night", "hour_of_day"]:
            if col not in df.columns:
                df[col] = 0

        weights     = get_training_weights()
        bounds      = get_training_bounds()
        df_n        = normalize_with_fixed_bounds(df, bounds)
        df_n["CLI"] = df_n.apply(lambda row: calculate_cli(row, weights), axis=1)
        latest      = df_n.iloc[-1]
        cli         = float(latest["CLI"])
        cat         = categorize_cli(cli)
        prev        = df_n["CLI"].iloc[:-1].tail(5)
        trend       = ("Up Rising"    if len(prev) and cli > prev.mean() + 0.05 else
                       "Down Falling" if len(prev) and cli < prev.mean() - 0.05 else
                       "Stable")

        return {
            "cli":      cli,
            "category": cat,
            "trend":    trend,
            "typing":   float(latest.get("typing_mean",   0)),
            "switches": int(latest.get("task_switching",  0)),
            "duration": float(latest.get("work_duration", 0)),
            "late":     int(latest.get("late_night",      0)),
            "sessions": len(df),
            "history":  list(df_n["CLI"].tail(14)),
            "no_data":  False,
        }
    except Exception as e:
        print(f"[Widget] Firestore error: {e}")
        return None


def save_to_firestore(uid):
    try:
        if not _init_fb():
            return
        from src.data.supabase_manager import save_session
        stats = get_safe_stats()
        save_session(uid, {
            "typing_mean":     stats["cpu"],
            "typing_variance": 0,
            "task_switching":  stats["proc"],
            "work_duration":   stats["duration"],
            "late_night":      stats["late"],
            "hour_of_day":     stats["hour"],
        })
        print(f"[Widget] Saved at {stats['time']}")
    except Exception as e:
        print(f"[Widget] Save error: {e}")


# ─────────────────────────── tray icon ──────────────────────────────

def _make_tray_image(color_hex: str = "#a8a4ff") -> "Image.Image":
    """Draw a 64×64 shield icon for the system tray."""
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    def hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    fill = hex_to_rgb(color_hex)

    # Shield polygon (normalised to 64×64)
    shield = [
        (32, 4),
        (56, 14),
        (56, 34),
        (32, 60),
        (8,  34),
        (8,  14),
    ]
    draw.polygon(shield, fill=fill + (230,))

    # Inner cutout so it looks like a shield outline
    inner = [(32, 12), (50, 20), (50, 34), (32, 52), (14, 34), (14, 20)]
    bg_dark = (30, 31, 46, 200)
    draw.polygon(inner, fill=bg_dark)

    return img


class TrayIcon:
    """Wraps pystray.Icon so we can update its color based on risk level."""

    def __init__(self, on_show, on_open_web, on_quit):
        self._on_show     = on_show
        self._on_open_web = on_open_web
        self._on_quit     = on_quit
        self._icon        = None
        self._current_col = "#a8a4ff"

    def start(self):
        if not TRAY_OK:
            return
        menu = pystray.Menu(
            pystray.MenuItem("Show Widget",   lambda icon, item: self._on_show()),
            pystray.MenuItem("Open Web App",  lambda icon, item: self._on_open_web()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit",          lambda icon, item: self._on_quit()),
        )
        self._icon = pystray.Icon(
            "BurnoutCopilot",
            _make_tray_image(self._current_col),
            "Burnout Co-pilot",
            menu,
        )
        # Run in its own daemon thread so it doesn't block tkinter
        t = threading.Thread(target=self._icon.run, daemon=True)
        t.start()

    def update_color(self, color_hex: str):
        if not TRAY_OK or self._icon is None:
            return
        if color_hex != self._current_col:
            self._current_col  = color_hex
            self._icon.icon    = _make_tray_image(color_hex)

    def stop(self):
        if TRAY_OK and self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass


# ─────────────────────────── widget ─────────────────────────────────

class BurnoutWidget:
    W      = 280
    H_FULL = 322
    H_MINI = 40

    def __init__(self):
        self.root        = tk.Tk()
        self._ox = self._oy = 0
        self._spark_vals = []
        self._minimised  = False   # compact 40px bar on screen
        self._hidden     = False   # sent to tray
        self._running    = True    # cleared on quit to stop background threads

        # Tray icon — callbacks reference widget methods defined below
        self._tray = TrayIcon(
            on_show     = self._show_from_tray,
            on_open_web = self._open_webapp,
            on_quit     = self._quit,
        )

        self._build()
        self._tray.start()
        self._start_topmost_loop()   # Win32: re-pin every 2 s without stealing focus
        self._schedule_save()
        self._refresh()

    # ───────── build UI ─────────

    def _build(self):
        r = self.root
        r.title("Burnout Co-pilot")
        r.geometry(f"{self.W}x{self.H_FULL}+40+80")
        r.resizable(False, False)
        r.overrideredirect(True)
        r.attributes("-topmost", True)
        r.attributes("-alpha", 0.97)
        r.configure(bg=BORDER)

        # Intercept WM_DELETE_WINDOW (just in case overrideredirect is lifted)
        r.protocol("WM_DELETE_WINDOW", self._hide_to_tray)

        self._outer = tk.Frame(r, bg=BG)
        self._outer.pack(fill="both", expand=True, padx=1, pady=1)
        self._build_titlebar(self._outer)
        self._build_body(self._outer)

    def _build_titlebar(self, parent):
        self._titlebar = tk.Frame(parent, bg=TITLEBAR, height=40)
        self._titlebar.pack(fill="x")
        self._titlebar.pack_propagate(False)

        # Shield logo
        cv = tk.Canvas(self._titlebar, width=22, height=22,
                       bg=TITLEBAR, highlightthickness=0)
        cv.pack(side="left", padx=(12, 6), pady=9)
        cv.create_polygon(11,1,20,5,20,13,11,20,2,13,2,5, fill=ACCENT, outline="")
        cv.create_polygon(11,5,17,8,17,13,11,18,5,13,5,8, fill=TITLEBAR, outline="")

        tk.Label(self._titlebar, text="Burnout Co-pilot",
                 bg=TITLEBAR, fg=TEXT,
                 font=("Segoe UI Semibold", 10)).pack(side="left")

        # × close → hides to tray
        self._close_btn = tk.Label(
            self._titlebar, text="×", bg=TITLEBAR, fg=MUTED,
            font=("Segoe UI", 13, "bold"), cursor="hand2", padx=10)
        self._close_btn.pack(side="right")
        self._close_btn.bind("<Button-1>", lambda _: self._hide_to_tray())
        self._close_btn.bind("<Enter>",    lambda _: self._close_btn.config(fg=HIGH_C))
        self._close_btn.bind("<Leave>",    lambda _: self._close_btn.config(fg=MUTED))

        # − / □  compact toggle
        self._min_btn = tk.Label(
            self._titlebar, text="−", bg=TITLEBAR, fg=MUTED,
            font=("Segoe UI", 13), cursor="hand2", padx=6)
        self._min_btn.pack(side="right")
        self._min_btn.bind("<Button-1>", lambda _: self._toggle_compact())
        self._min_btn.bind("<Enter>",    lambda _: self._min_btn.config(fg=ACCENT))
        self._min_btn.bind("<Leave>",    lambda _: self._min_btn.config(fg=MUTED))

        self._titlebar.bind("<Button-1>",  self._drag_start)
        self._titlebar.bind("<B1-Motion>", self._drag_move)

    def _build_body(self, parent):
        self._body = tk.Frame(parent, bg=BG)
        self._body.pack(fill="both", expand=True)
        self._build_risk_panel(self._body)
        tk.Frame(self._body, bg=BORDER, height=1).pack(fill="x")
        self._build_stats(self._body)
        tk.Frame(self._body, bg=BORDER, height=1).pack(fill="x")
        self._build_footer(self._body)

    def _build_risk_panel(self, p):
        panel = tk.Frame(p, bg=BG2, pady=12, padx=18)
        panel.pack(fill="x")

        top = tk.Frame(panel, bg=BG2)
        top.pack(fill="x")

        self._v_cli   = tk.StringVar(value="--")
        self._cli_lbl = tk.Label(top, textvariable=self._v_cli,
                                 bg=BG2, fg=ACCENT,
                                 font=("Segoe UI Light", 42))
        self._cli_lbl.pack(side="left", anchor="s")

        right = tk.Frame(top, bg=BG2)
        right.pack(side="left", anchor="s", padx=(10, 0), pady=(0, 6))

        self._v_badge = tk.StringVar(value="")
        self._badge   = tk.Label(right, textvariable=self._v_badge,
                                 bg=ACCENT, fg=TITLEBAR,
                                 font=("Segoe UI Semibold", 8),
                                 padx=7, pady=3)
        self._badge.pack(anchor="w")

        self._v_sub = tk.StringVar(value="")
        tk.Label(right, textvariable=self._v_sub,
                 bg=BG2, fg=MUTED,
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))

        self._spark = tk.Canvas(panel, width=244, height=26,
                                bg=BG2, highlightthickness=0)
        self._spark.pack(pady=(8, 2))

        self._signin_btn = tk.Label(
            panel, text="  Sign in for full insights  →  ",
            bg=ACCENT, fg=TITLEBAR,
            font=("Segoe UI Semibold", 9),
            cursor="hand2", pady=4)
        self._signin_btn.bind("<Button-1>", lambda _: self._open_webapp())
        self._signin_btn.bind("<Enter>",    lambda _: self._signin_btn.config(bg="#c4c0ff"))
        self._signin_btn.bind("<Leave>",    lambda _: self._signin_btn.config(bg=ACCENT))

    def _build_stats(self, p):
        frame = tk.Frame(p, bg=BG, pady=8, padx=18)
        frame.pack(fill="x")
        self._svars = {}
        for key, icon, label in [
            ("duration", "O", "Work Duration"),
            ("hour",     "@", "Current Hour"),
            ("late",     "~", "Late Night"),
        ]:
            row = tk.Frame(frame, bg=BG)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=icon, bg=BG, fg=ACCENT,
                     font=("Segoe UI", 11), width=2, anchor="w").pack(side="left")
            tk.Label(row, text=label, bg=BG, fg=MUTED,
                     font=("Segoe UI", 9), anchor="w", width=15).pack(side="left")
            v   = tk.StringVar(value="--")
            lbl = tk.Label(row, textvariable=v, bg=BG, fg=TEXT,
                           font=("Segoe UI Semibold", 9), anchor="e")
            lbl.pack(side="right")
            self._svars[key] = (v, lbl)

    def _build_footer(self, p):
        foot = tk.Frame(p, bg=BG, padx=18, pady=7)
        foot.pack(fill="x")
        self._v_status = tk.StringVar(value="Starting…")
        tk.Label(foot, textvariable=self._v_status,
                 bg=BG, fg=MUTED,
                 font=("Segoe UI", 7), anchor="w").pack(side="left")
        ref = tk.Label(foot, text="↺", bg=BG, fg=MUTED,
                       font=("Segoe UI", 11), cursor="hand2")
        ref.pack(side="right")
        ref.bind("<Enter>",    lambda _: ref.config(fg=ACCENT))
        ref.bind("<Leave>",    lambda _: ref.config(fg=MUTED))
        ref.bind("<Button-1>", lambda _: self._fetch_async())

    # ───────── always-on-top enforcement ─────────

    def _start_topmost_loop(self):
        """
        Spawn a daemon thread that re-applies HWND_TOPMOST every 2 seconds.

        Why this is needed:
          tkinter's -topmost flag loses the fight after:
            • screen unlock / lock
            • UAC prompts
            • some full-screen games / video players
            • Windows snapping another window over it

          Win32 SetWindowPos with HWND_TOPMOST + SWP_NOACTIVATE re-pins the
          widget without stealing keyboard focus or causing flicker.
        """
        if not WIN32_OK:
            return
        t = threading.Thread(target=self._enforce_topmost, daemon=True)
        t.start()

    def _enforce_topmost(self):
        """Background loop: re-pin widget to top of Z-order every 2 s."""
        while self._running:
            time.sleep(2)
            if self._hidden or self._running is False:
                continue
            try:
                # Get the real Win32 HWND from tkinter
                hwnd = self.root.winfo_id()
                _user32.SetWindowPos(
                    hwnd,
                    _HWND_TOPMOST,
                    0, 0, 0, 0,          # x, y, w, h ignored by SWP_NOMOVE|NOSIZE
                    _SWP_FLAGS,
                )
            except Exception:
                pass   # non-Windows or window not yet created — silently skip

    # ───────── window management ─────────

    def _hide_to_tray(self):
        """Hide widget window; logging keeps running. Tray icon stays."""
        self._hidden = True
        self.root.withdraw()          # invisible but alive
        print("[Widget] Hidden to tray. Logging continues.")

    def _show_from_tray(self):
        """Restore widget from tray — called from tray menu (non-tk thread)."""
        self.root.after(0, self._do_show)

    def _do_show(self):
        self._hidden = False
        self.root.deiconify()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.lift()

    def _toggle_compact(self):
        """Shrink to 40px title bar or restore full — stays on screen."""
        if self._minimised:
            self._body.pack(fill="both", expand=True)
            self.root.geometry(f"{self.W}x{self.H_FULL}")
            self._min_btn.config(text="−")
            self._minimised = False
        else:
            self._body.pack_forget()
            self.root.geometry(f"{self.W}x{self.H_MINI}")
            self._min_btn.config(text="□")
            self._minimised = True

    def _drag_start(self, e):
        self._ox = e.x_root - self.root.winfo_x()
        self._oy = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        self.root.geometry(f"+{e.x_root - self._ox}+{e.y_root - self._oy}")

    def _open_webapp(self):
        import webbrowser
        webbrowser.open(WEB_APP_URL)

    def _quit(self):
        """Fully exit — stops background threads, tray icon, destroys window."""
        print("[Widget] Quit requested from tray.")
        self._running = False      # stops _enforce_topmost loop
        self._tray.stop()
        self.root.after(0, self.root.destroy)

    # ───────── stats helpers ─────────

    def _set_stat(self, key, text, color=None):
        v, lbl = self._svars[key]
        v.set(text)
        lbl.config(fg=color if color else TEXT)

    def _draw_spark(self, vals):
        c = self._spark
        c.delete("all")
        if not vals:
            return
        n   = min(len(vals), 14)
        vs  = vals[-n:]
        w, h = 244, 26
        bar  = w / (n * 1.7)
        gap  = (w - bar * n) / (n + 1)
        mx   = max(vs) if max(vs) > 0 else 1
        for i, v in enumerate(vs):
            x1  = gap + i * (bar + gap)
            x2  = x1 + bar
            bh  = max(3, int((v / mx) * (h - 4)))
            col = HIGH_C if v >= 0.7 else MID_C if v >= 0.4 else LOW_C
            c.create_rectangle(x1, h - bh, x2, h, fill=col, outline="", width=0)

    # ───────── data cycle ─────────

    def _schedule_save(self):
        self._do_save()

    def _do_save(self):
        creds = load_credentials()
        if creds:
            threading.Thread(target=save_to_firestore,
                             args=(creds["uid"],), daemon=True).start()
        self.root.after(SAVE_MS, self._do_save)

    def _refresh(self):
        self._fetch_async()
        self.root.after(REFRESH_MS, self._refresh)

    def _fetch_async(self):
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        creds = load_credentials()
        stats = get_safe_stats()
        fs    = fetch_firestore_stats(creds["uid"]) if creds else None
        self.root.after(0, lambda: self._render(stats, fs, creds))

    # ───────── render ─────────

    def _render(self, stats, fs, creds):
        if self._minimised:
            return

        # Update tray icon color to match current risk
        if creds and fs and "cli" in fs:
            self._tray.update_color(RISK_COLOR.get(fs["category"], ACCENT))
        else:
            self._tray.update_color(RISK_COLOR.get(stats["local_cat"], ACCENT))

        hour = stats["hour"]
        now  = stats["time"]

        if creds and fs and "cli" in fs:
            cli = fs["cli"]
            cat = fs["category"]
            col = RISK_COLOR.get(cat, ACCENT)
            self._v_cli.set(f"{cli:.2f}")
            self._cli_lbl.config(fg=col)
            self._v_badge.set(f"  {RISK_LABEL.get(cat, '?')}  ")
            self._badge.config(bg=col, fg=TITLEBAR)
            self._v_sub.set(fs.get("trend", ""))
            self._signin_btn.pack_forget()
            self._spark_vals = fs.get("history", [cli])
            self._draw_spark(self._spark_vals)
            self._set_stat("duration", f"{fs['duration']:.1f} hrs")
            self._set_stat("hour",     f"{hour:02d}:00")
            self._set_stat("late",     "Yes" if fs["late"] else "No",
                           HIGH_C if fs["late"] else LOW_C)
            name = creds.get("name",
                creds["email"].split("@")[0].replace(".", " ").title())
            self._v_status.set(
                f"{name}  ·  {fs['sessions']} sessions  ·  {now}")

        elif creds and fs and fs.get("no_data"):
            self._render_local(stats, "No sessions yet – tracker running")
            self._signin_btn.pack_forget()
            name = creds.get("name",
                creds["email"].split("@")[0].replace(".", " ").title())
            self._v_status.set(f"{name}  ·  No sessions yet  ·  {now}")

        else:
            self._render_local(stats, "Sign in for full analysis")
            self._signin_btn.pack(fill="x", pady=(6, 0))
            self._v_status.set(f"Local estimate  ·  {now}")

    def _render_local(self, stats, note=""):
        cli = stats["local_cli"]
        cat = stats["local_cat"]
        col = RISK_COLOR.get(cat, ACCENT)
        self._v_cli.set(f"{cli:.2f}")
        self._cli_lbl.config(fg=col)
        self._v_badge.set(f"  {RISK_LABEL.get(cat, '?')}  ")
        self._badge.config(bg=col, fg=TITLEBAR)
        self._v_sub.set(note)
        self._spark_vals.append(cli)
        if len(self._spark_vals) > 20:
            self._spark_vals = self._spark_vals[-20:]
        self._draw_spark(self._spark_vals)
        self._set_stat("duration", f"{stats['duration']:.2f} hrs")
        self._set_stat("hour",     f"{stats['hour']:02d}:00")
        self._set_stat("late",     "Yes" if stats["late"] else "No",
                       HIGH_C if stats["late"] else LOW_C)

    def run(self):
        self.root.mainloop()


# ─────────────────────────── startup registration ───────────────────

def register_startup():
    script  = Path(__file__).resolve()
    project_dir = script.parent 
    vbs     = script.with_name("burnout_launch.vbs")
    
    # Point EXACTLY to your virtual environment's python
    python_exe = str(project_dir / "friend_env" / "Scripts" / "python.exe")

    vbs_src = (
        'Set WshShell = CreateObject("WScript.Shell")\n'
        f'WshShell.CurrentDirectory = "{project_dir}"\n'
        f'WshShell.Run Chr(34) & "{python_exe}" & Chr(34) & " " & '
        f'Chr(34) & "{script}" & Chr(34), 0, False\n'
    )

    try:
        vbs.write_text(vbs_src, encoding="utf-8")
        print(f"[Startup] Launcher updated for friend_env.")
    except Exception as e:
        print(f"[Startup] Error: {e}")
        return

    task = "BurnoutCopilotWidget"
    # Delete old task first to be safe
    subprocess.run(["schtasks", "/delete", "/tn", task, "/f"], capture_output=True)
    
    # Create the new one
    subprocess.run([
        "schtasks", "/create", "/tn", task,
        "/tr", f'wscript.exe "{vbs}"',
        "/sc", "ONLOGON", "/rl", "HIGHEST", "/f"
    ])
    
    # Force Start
    subprocess.run(["schtasks", "/run", "/tn", task])
    print("[Startup] Task registered and started. Check your screen/tray.")


# ─────────────────────────── entrypoint ──────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Burnout Co-pilot Desktop Widget")
    parser.add_argument("--register-startup", action="store_true",
                        help="Register widget to launch automatically at login (run as Admin)")
    args = parser.parse_args()

    if args.register_startup:
        register_startup()
        return

    widget = BurnoutWidget()
    widget.run()


if __name__ == "__main__":
    main()