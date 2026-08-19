# startup_logger.py
"""
Standalone startup logger for Burnout Co-pilot.

PURPOSE
-------
Runs PyLogger at device boot (before the user opens the Streamlit app).
Reads the saved user UID from a local credentials file so it can push
sessions to Supabase immediately - even before the user logs in to the web app.

HOW TO SET UP (Windows)
-----------------------
1. Place this file in your project root (same folder as app.py).
2. Run once manually after login to save credentials:
       python startup_logger.py --save-credentials
3. Register as a Windows startup task (run once as admin):
       python startup_logger.py --register-startup
   OR manually: add a shortcut to this script in
       shell:startup  (Win+R -> shell:startup)
   pointing to:
       pythonw.exe  C:\\path\\to\\burnout_project\\startup_logger.py

HOW TO SET UP (macOS / Linux)
------------------------------
Add to crontab:
    @reboot cd /path/to/burnout_project && /path/to/venv/bin/python startup_logger.py &
"""

import sys
import os
import json
import time
import logging
import argparse
import threading
from pathlib import Path

# -- Ensure project root is on sys.path ---------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# -- Credentials file (stores uid so tracker can push to Supabase at boot) ----
CREDS_FILE = PROJECT_ROOT / ".burnout_local_creds.json"

# -- Force UTF-8 output, unconditionally ---------------------------------------
# WHY THIS IS HERE: Windows' console defaults to the cp1252 code page,
# which cannot represent most Unicode symbols (emoji have no cp1252
# byte at all). Manually deleting emoji from log messages one at a time
# is fragile -- tracker.py (which this script runs) still logs things
# like "Keyboard listener started" and "PyLogger started" WITH emoji,
# and any of those would hit the exact same crash-diagnostic the
# moment a session saves. Reconfiguring stdout/stderr to UTF-8 here,
# once, at the actual process entrypoint, fixes it for every module
# this script imports -- permanently, even if emoji get added back
# anywhere later. This does nothing on non-Windows platforms (they
# already default to UTF-8), and does nothing harmful if it can't run
# (very old Python) -- it just gets skipped.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="[StartupLogger %(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        # encoding="utf-8" here fixes the SAME class of error for the
        # log FILE too -- without it, FileHandler uses the system's
        # default codepage (cp1252 on Windows) just like the console did.
        logging.FileHandler(PROJECT_ROOT / "startup_logger.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("startup_logger")


# -- Credential helpers --------------------------------------------------------

def save_credentials(uid: str, email: str):
    """Saves uid + email to a local JSON file for boot-time use."""
    data = {"uid": uid, "email": email}
    CREDS_FILE.write_text(json.dumps(data), encoding="utf-8")
    log.info(f"Credentials saved for {email} ({uid})")


def load_credentials() -> dict | None:
    """Loads saved credentials. Returns None if file missing or corrupt."""
    if not CREDS_FILE.exists():
        log.warning(f"No credentials file found at {CREDS_FILE}. "
                    "Run with --save-credentials first.")
        return None
    try:
        data = json.loads(CREDS_FILE.read_text(encoding="utf-8"))
        if "uid" in data and "email" in data:
            return data
    except Exception as e:
        log.error(f"Failed to read credentials: {e}")
    return None


def clear_credentials():
    """Removes saved credentials (call on logout)."""
    if CREDS_FILE.exists():
        CREDS_FILE.unlink()
        log.info("Credentials cleared.")


# -- Windows startup registration ----------------------------------------------

def register_windows_startup():
    """Adds this script to the Windows Task Scheduler to run at boot."""
    try:
        import subprocess
        python_exe = sys.executable.replace("python.exe", "pythonw.exe")
        script     = str(Path(__file__).resolve())
        task_name  = "BurnoutCopilotLogger"

        cmd = [
            "schtasks", "/create", "/tn", task_name,
            "/tr", f'"{python_exe}" "{script}"',
            "/sc", "ONLOGON",
            "/rl", "HIGHEST",
            "/f",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            log.info(f"Startup task '{task_name}' registered successfully.")
            print("\nDone! PyLogger will now start automatically at every login.")
        else:
            log.error(f"Failed to register task: {result.stderr}")
            print("\nFailed. Try running this script as Administrator.")
    except FileNotFoundError:
        log.error("schtasks not found - this only works on Windows.")


# -- Interactive credential save -----------------------------------------------

def interactive_save_credentials():
    """Prompts the user for email + password, authenticates, and saves the UID."""
    print("\n-- Burnout Co-pilot: Save Login Credentials --")
    print("These are stored locally so PyLogger can run at startup.\n")

    email    = input("Email: ").strip()
    password = input("Password: ").strip()

    # Initialise Supabase before auth
    from src.auth.supabase_client import init_supabase
    init_supabase()

    from src.auth.auth_manager import login
    result = login(email, password)

    if result["success"]:
        save_credentials(result["uid"], result["email"])
        print(f"\nCredentials saved for {result['display_name']} ({email})")
        print("You can now run --register-startup or restart your PC.")
    else:
        print(f"\nLogin failed: {result['error']}")


# -- Main tracker entrypoint ---------------------------------------------------

def run_logger():
    """
    Main function: initialises Supabase + tracker, then blocks forever.
    Called at boot by the startup task.
    """
    log.info("Burnout Co-pilot startup logger initialising...")

    creds = load_credentials()
    if not creds:
        log.error("No saved credentials - cannot start tracker. "
                  "Run: python startup_logger.py --save-credentials")
        sys.exit(1)

    uid   = creds["uid"]
    email = creds["email"]
    log.info(f"Loaded credentials for {email} (uid={uid})")

    # Initialise Supabase
    try:
        from src.auth.supabase_client import init_supabase
        init_supabase()
        log.info("Supabase initialised")
    except Exception as e:
        log.error(f"Supabase init failed: {e}")
        sys.exit(1)

    # Start the tracker
    try:
        from src.data.tracker import start_tracker, is_running
        start_tracker(uid)
        log.info(f"PyLogger started for uid={uid}")
    except Exception as e:
        log.error(f"Tracker failed to start: {e}")
        sys.exit(1)

    # Keep the process alive (tracker threads are daemons so we must block)
    log.info("Startup logger running. Sessions will be saved to Supabase every hour.")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        log.info("Startup logger stopped by user.")
        from src.data.tracker import stop_tracker
        stop_tracker()


# -- CLI -----------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Burnout Co-pilot Startup Logger")
    parser.add_argument("--save-credentials",  action="store_true",
                        help="Interactively save login credentials for boot-time use")
    parser.add_argument("--register-startup",  action="store_true",
                        help="Register this script as a Windows startup task (run as admin)")
    parser.add_argument("--clear-credentials", action="store_true",
                        help="Remove saved credentials")
    args = parser.parse_args()

    if args.save_credentials:
        interactive_save_credentials()
    elif args.register_startup:
        register_windows_startup()
    elif args.clear_credentials:
        clear_credentials()
    else:
        run_logger()