from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.auth import verify_jwt_token
from app.config import settings

security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    FastAPI dependency to extract and verify the current authenticated user_id.

    Security: returns HTTP 401 when no credentials are provided.
    The dev UUID fallback is only permitted when DEBUG=True (local development only).
    """
    if not credentials:
        if settings.DEBUG:
            # Allow unauthenticated calls in local dev only
            return "00000000-0000-0000-0000-000000000000"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    user_id = verify_jwt_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id

