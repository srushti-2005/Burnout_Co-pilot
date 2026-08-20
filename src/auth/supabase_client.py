"""
Supabase client factory.

Uses:
- SUPABASE_ANON_KEY for authentication operations.
- SUPABASE_SERVICE_ROLE_KEY for trusted server-side data operations.

Configuration is loaded from:
1. Streamlit secrets (deployment)
2. .env file (local development)
3. Environment variables
"""

import os
import logging

import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Load local .env
# ---------------------------------------------------------------------------

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))
_ENV_PATH = os.path.join(_PROJECT_ROOT, ".env")

load_dotenv(_ENV_PATH)


# ---------------------------------------------------------------------------
# Load Supabase configuration
#
# Streamlit Cloud:
#     st.secrets
#
# Local development:
#     .env / environment variables
# ---------------------------------------------------------------------------

SUPABASE_URL = st.secrets.get(
    "SUPABASE_URL",
    os.getenv("SUPABASE_URL")
)

SUPABASE_ANON_KEY = st.secrets.get(
    "SUPABASE_ANON_KEY",
    os.getenv("SUPABASE_ANON_KEY")
)

SUPABASE_SERVICE_ROLE_KEY = st.secrets.get(
    "SUPABASE_SERVICE_ROLE_KEY",
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)


# ---------------------------------------------------------------------------
# Configuration validation
# ---------------------------------------------------------------------------

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError(
        "SUPABASE_URL / SUPABASE_ANON_KEY not configured. "
        "For Streamlit Cloud, add them under App Settings → Secrets. "
        "For local development, add them to .env."
    )


# ---------------------------------------------------------------------------
# Authentication client
# ---------------------------------------------------------------------------

def get_auth_client() -> Client:
    """
    Anon-key client.

    Used only for:
    - sign in
    - sign up
    - sign out
    - password reset
    """
    return create_client(
        SUPABASE_URL,
        SUPABASE_ANON_KEY
    )


# ---------------------------------------------------------------------------
# Trusted server-side client
# ---------------------------------------------------------------------------

def get_service_client() -> Client:
    """
    Service-role client.

    Used only by trusted server-side Python code for:
    - sessions
    - profiles
    - baselines
    - other server-side database operations

    NEVER expose the service-role key to a browser/mobile client.
    """

    if not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY not configured. "
            "Add it to Streamlit Cloud Secrets or your local .env file."
        )

    return create_client(
        SUPABASE_URL,
        SUPABASE_SERVICE_ROLE_KEY
    )


# ---------------------------------------------------------------------------
# Backwards compatibility
# ---------------------------------------------------------------------------

def init_supabase():
    """
    Compatibility function for existing code.

    Validates that the service-role configuration is available.
    """
    get_service_client()
    return True


# Old Firebase-compatible name
init_firebase = init_supabase