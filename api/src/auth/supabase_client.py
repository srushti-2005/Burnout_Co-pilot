# src/auth/supabase_client.py
"""
Supabase client factory.
Replaces: src/auth/firebase_init.py

WHY TWO CLIENTS, NOT ONE
------------------------
Your old Firebase setup used the Admin SDK (firebase_credentials.json,
a service account) inside tracker.py / burnout_widget.py / startup_logger.py.
That gave those trusted, first-party Python scripts full access to
Firestore, bypassing security rules — they just passed a plain `uid`
string around and trusted it.

The direct Supabase equivalent of "Admin SDK" is the **service_role**
key. So:

  get_auth_client()    -> anon key. ONLY for auth.sign_in / sign_up /
                           sign_out / reset_password. This is the
                           public-facing part (equivalent to Firebase's
                           client-side email/password REST calls you
                           had before).

  get_service_client() -> service_role key. Used by supabase_manager.py
                           (sessions/profiles reads+writes) from
                           tracker.py, burnout_widget.py, startup_logger.py,
                           and app.py's data layer. This bypasses Row
                           Level Security intentionally — exactly like
                           the Admin SDK bypassed Firestore rules —
                           because these are trusted, first-party
                           Python processes, not a browser.

WHY NO GLOBAL SINGLETON
------------------------
An earlier draft cached a single shared Client at module level.
That's fine for a single-user desktop widget process, but NOT safe if
app.py is ever deployed as a normal Streamlit server (one Python
process serving many browsers at once, each in its own thread) —
a shared client object could leak one user's Postgrest state into
another user's request. Building a fresh client per call costs a few
milliseconds and completely avoids that class of bug, so that's what
this module does.
"""

# src/auth/supabase_client.py
import os
import logging

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    logger.warning("SUPABASE_URL / SUPABASE_ANON_KEY not set — Supabase features will fail at request time, not at import time.")

def get_service_client():
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError("Supabase not configured. Check environment variables.")
    # ... existing client creation code

from supabase import create_client, Client
from dotenv import load_dotenv

# Same fix as cli_logic.py's DEFAULT_DATA_PATH: resolve .env relative
# to THIS file's location, not the process's working directory. Without
# this, load_dotenv() with no path relies on locating .env via the call
# stack, which is not guaranteed to work when launched by Task
# Scheduler with an unexpected working directory.
_THIS_DIR     = os.path.dirname(os.path.abspath(__file__))   # .../src/auth
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))  # up two levels -> project root
_ENV_PATH     = os.path.join(_PROJECT_ROOT, ".env")

load_dotenv(_ENV_PATH)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError(
        "SUPABASE_URL / SUPABASE_ANON_KEY not set. "
        "Create a .env file in your project root (see .env.example)."
    )


def get_auth_client() -> Client:
    """Anon-key client — use ONLY for auth.sign_in/sign_up/sign_out/reset calls."""
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def get_service_client() -> Client:
    """
    Service-role client — full trusted access, bypasses RLS.
    Use for all sessions/profiles/baselines reads+writes from
    tracker.py, burnout_widget.py, startup_logger.py, and app.py.

    NEVER import this into anything that ships to a browser or mobile
    app directly (e.g. a future Flutter/React Native client should call
    your FastAPI backend, not hold this key itself).
    """
    if not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY not set in .env. "
            "Get it from Supabase Dashboard -> Project Settings -> API "
            "(the 'service_role secret' key, not 'anon public')."
        )
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def init_supabase():
    """
    Kept for drop-in compatibility with the old init_firebase() call
    pattern in app.py / burnout_widget.py / startup_logger.py.
    Just validates that env vars are present; no persistent state to
    build (unlike Firebase Admin SDK, Supabase clients are cheap and
    created fresh per call — see module docstring above).
    """
    get_service_client()  # raises immediately with a clear error if misconfigured
    return True


# ── Backwards-compatible alias ────────────────────────────────────────────
# Lets any file still doing `from src.auth.firebase_init import init_firebase`
# switch to `from src.auth.supabase_client import init_firebase` without
# touching the rest of that file.
init_firebase = init_supabase
