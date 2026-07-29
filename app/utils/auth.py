from jose import jwt, JWTError
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def verify_jwt_token(token: str) -> str | None:
    """
    Decodes Supabase JWT token and extracts the user_id (sub).
    If JWT_SECRET is provided, verifies signature; otherwise attempts decoding payload safely.
    """
    try:
        if settings.JWT_SECRET:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
        else:
            # Fallback unverified decode for development
            payload = jwt.get_unverified_claims(token)
        
        user_id = payload.get("sub")
        return user_id
    except JWTError as e:
        logger.warning(f"JWT Verification failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected auth decoding error: {e}")
        return None
