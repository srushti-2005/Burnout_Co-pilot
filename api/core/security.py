"""
Verifies the user's token by asking Supabase itself, instead of
manually checking the JWT signature. This works no matter which
signing algorithm your Supabase project uses (HS256 shared-secret or
newer ES256/RS256 key pairs) — Supabase always knows how to check its
own tokens, so we just ask it.
"""
from fastapi import Header, HTTPException, status
from core.supabase_client import get_service_client


def get_current_user_id(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )
    token = authorization.removeprefix("Bearer ").strip()

    try:
        client = get_service_client()
        response = client.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    if not response or not response.user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    return response.user.id