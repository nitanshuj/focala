from jose import jwt, JWTError
from app.config import settings
import logging
import base64

logger = logging.getLogger(__name__)

def _decode_jwt(token: str, key: str | bytes) -> dict | None:
    """Attempt to decode and verify a JWT with the given key. Returns payload or None."""
    try:
        return jwt.decode(token, key, algorithms=["HS256"], options={"verify_aud": False})
    except JWTError:
        return None

def verify_jwt_token(token: str) -> str | None:
    """
    Verifies a Supabase JWT token and returns the user_id (sub).

    Strategy:
    1. Dev bypass  — only when DEBUG=True and token starts with 'dev-'.
    2. Fast local decode — tries the JWT_SECRET as both a raw string AND as
       base64-decoded bytes (Supabase dashboard shows the secret base64-encoded,
       but signs tokens with the decoded raw bytes).
    3. Authoritative fallback — calls supabase.auth.get_user(token) if both
       local attempts fail. Always correct; costs one network round-trip.

    To guarantee the fast-path always succeeds without the fallback, set
    JWT_SECRET to the value from:
    Supabase Dashboard → Project Settings → API → JWT Secret
    """
    if not token:
        return None

    # 1. Dev-mode bypass — only permitted when DEBUG=True
    if settings.DEBUG and token.startswith("dev-"):
        logger.warning("Dev token accepted — DEBUG mode only. Never use in production.")
        return "00000000-0000-0000-0000-000000000000"

    # 2. Fast-path: local JWT verification (no network call)
    if settings.JWT_SECRET:
        # Try A: raw secret string as-is
        payload = _decode_jwt(token, settings.JWT_SECRET)

        # Try B: base64-decoded bytes (Supabase dashboard shows secret as base64)
        if payload is None:
            try:
                decoded_key = base64.b64decode(settings.JWT_SECRET)
                payload = _decode_jwt(token, decoded_key)
            except Exception:
                pass

        if payload is not None:
            user_id = payload.get("sub")
            if user_id:
                return user_id

        logger.debug(
            "Local JWT decode failed with both raw and base64-decoded JWT_SECRET. "
            "Falling back to Supabase auth API."
        )

    # 3. Authoritative fallback: Supabase verifies its own token
    try:
        from app.services.supabase_client import supabase
        response = supabase.auth.get_user(token)
        if response and response.user:
            return str(response.user.id)
        logger.warning("Supabase auth.get_user returned no user for the provided token.")
        return None
    except Exception as e:
        logger.warning(f"JWT verification failed via Supabase auth API: {str(e)[:200]}")
        return None
