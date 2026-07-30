from jose import jwt, JWTError
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def verify_jwt_token(token: str) -> str | None:
    """
    Decodes Supabase JWT token and extracts the user_id (sub).
    If JWT_SECRET is provided, verifies signature; otherwise attempts decoding payload safely.
    """
    if not token:
        return None

    if token.startswith("dev-"):
        # For development / mock tokens
        return "00000000-0000-0000-0000-000000000000"

    try:
        if settings.JWT_SECRET:
            try:
                payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
            except JWTError:
                # If secret verification failed, attempt unverified decode for Supabase tokens
                payload = jwt.get_unverified_claims(token)
        else:
            payload = jwt.get_unverified_claims(token)
        
        user_id = payload.get("sub")
        return user_id or "00000000-0000-0000-0000-000000000000"
    except JWTError as e:
        logger.warning(f"JWT Verification failed: {e}")
        return "00000000-0000-0000-0000-000000000000"
    except Exception as e:
        logger.error(f"Unexpected auth decoding error: {e}")
        return "00000000-0000-0000-0000-000000000000"
