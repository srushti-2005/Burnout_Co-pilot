# src/auth/auth_manager.py
"""
Handles user login, signup and logout.
Uses Supabase Auth (email + password).

Replaces the old Firebase Identity Toolkit REST calls. Function names
and return-value shapes are kept IDENTICAL to the old file, so app.py
does not need to change at all — only the import path changes:

    OLD: from src.auth.auth_manager import login, signup, logout, reset_password
    NEW: from src.auth.auth_manager import login, signup, logout, reset_password
         (same line — this file is a drop-in replacement)

Client usage note: auth.* calls use the anon-key client (get_auth_client) —
that's the public-facing part, same trust level as your old Firebase
client-side sign-in calls. The profiles table read/write uses the
service-role client (get_service_client) so it always succeeds
regardless of session/RLS state, mirroring how your old signup() wrote
to Firestore via the Admin SDK.
"""

import streamlit as st
from src.auth.supabase_client import get_auth_client, get_service_client


# ── internal helpers ──────────────────────────────────────────────────────

def _upsert_profile(uid: str, email: str, display_name: str):
    """Writes/updates the profiles row. Non-fatal if it fails."""
    try:
        get_service_client().table("profiles").upsert({
            "id": uid,
            "email": email,
            "display_name": display_name,
        }).execute()
    except Exception as e:
        log.error(f"[auth_manager] profile upsert failed: {e}")


def _get_display_name(uid: str, email: str) -> str:
    """Fetches display_name from the profiles table, falling back to email."""
    try:
        res = (
            get_service_client()
            .table("profiles")
            .select("display_name")
            .eq("id", uid)
            .single()
            .execute()
        )
        if res.data and res.data.get("display_name"):
            return res.data["display_name"]
    except Exception:
        pass
    return email.split("@")[0].replace(".", " ").title()


# ── public API (same signatures as the old Firebase version) ─────────────

def login(email: str, password: str) -> dict:
    """
    Signs in an existing user.
    Returns dict with keys: success, uid, email, display_name, id_token, error
    """
    try:
        res = get_auth_client().auth.sign_in_with_password({
            "email": email, "password": password
        })

        if not res.user or not res.session:
            return {"success": False, "error": "Incorrect email or password."}

        uid = res.user.id
        display_name = _get_display_name(uid, res.user.email)

        return {
            "success": True,
            "uid": uid,
            "email": res.user.email,
            "display_name": display_name,
            "id_token": res.session.access_token,   # kept as "id_token" for compatibility
        }

    except Exception as e:
        return {"success": False, "error": _friendly_error(str(e))}


def signup(email: str, password: str, display_name: str) -> dict:
    """
    Creates a new user account and a matching profiles row.
    Returns same dict structure as login().

    NOTE: by default, Supabase requires email confirmation before a
    session is issued (unlike Firebase, which logged users in
    immediately). If you want the old "signup -> instantly logged in"
    behaviour, go to Supabase Dashboard -> Authentication -> Providers
    -> Email and turn OFF "Confirm email". Otherwise, res.session will
    be None here and id_token will be None until the user clicks the
    confirmation link — you may want to show a "check your inbox"
    message in app.py's sign-up tab for that case (r["id_token"] is None).
    """
    try:
        res = get_auth_client().auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"display_name": display_name}},
        })

        if not res.user:
            return {"success": False, "error": "Signup failed."}

        uid = res.user.id

        # The DB trigger (see schema.sql) already creates a profiles row
        # on auth.users insert, but we upsert here too in case
        # display_name needs updating.
        _upsert_profile(uid, email, display_name)

        id_token = res.session.access_token if res.session else None

        return {
            "success": True,
            "uid": uid,
            "email": email,
            "display_name": display_name,
            "id_token": id_token,
        }

    except Exception as e:
        return {"success": False, "error": _friendly_error(str(e))}


def reset_password(email: str) -> dict:
    """Sends a password reset email."""
    try:
        get_auth_client().auth.reset_password_for_email(email)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def logout():
    """Signs out of Supabase and clears session state keys."""
    try:
        get_auth_client().auth.sign_out()
    except Exception:
        pass
    for key in ["user_uid", "user_email", "user_name", "id_token", "logged_in"]:
        st.session_state.pop(key, None)


def _friendly_error(msg: str) -> str:
    m = msg.lower()
    mapping = {
        "invalid login credentials": "Incorrect email or password.",
        "user already registered":   "An account with this email already exists.",
        "password should be at least": "Password must be at least 6 characters.",
        "unable to validate email address": "Please enter a valid email address.",
        "email not confirmed":       "Please confirm your email before logging in.",
        "email rate limit exceeded": "Too many attempts. Try again later.",
        # Network/DNS failures -- e.g. Windows' "[Errno 11001] getaddrinfo
        # failed", macOS/Linux's "nodename nor servname provided", or a
        # generic connection timeout. These mean the request never even
        # reached Supabase -- almost always no internet connection, a
        # firewall/VPN blocking *.supabase.co, or SUPABASE_URL in .env
        # being wrong/still the placeholder from .env.example.
        "getaddrinfo failed":        "Can't reach the server. Check your internet connection.",
        "nodename nor servname":     "Can't reach the server. Check your internet connection.",
        "name or service not known": "Can't reach the server. Check your internet connection.",
        "connection refused":        "Can't reach the server. Check your internet connection.",
        "timed out":                 "The connection timed out. Check your internet connection and try again.",
        "connecterror":              "Can't reach the server. Check your internet connection.",
    }
    for key, friendly in mapping.items():
        if key in m:
            return friendly
    return msg
