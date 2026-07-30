from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
import logging
import uuid

from app.models.auth import SignUpRequest, LoginRequest, ResetPasswordRequest, AuthResponse, UserResponse
from app.services.supabase_client import supabase
from app.dependencies import get_current_user
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignUpRequest):
    """
    Registers a new user with Supabase Auth or returns a dev session token.
    """
    try:
        # 1. Attempt Supabase Auth Sign Up
        res = supabase.auth.sign_up({
            "email": payload.email,
            "password": payload.password,
            "options": {
                "data": {
                    "display_name": payload.display_name or payload.email.split("@")[0]
                }
            }
        })
        
        user_id = str(res.user.id) if (res and res.user) else str(uuid.uuid4())
        access_token = res.session.access_token if (res and res.session) else f"dev-token-{user_id}"
        
        # Ensure user profile exists in profiles table
        try:
            supabase.table("profiles").upsert({
                "id": user_id,
                "email": payload.email,
                "display_name": payload.display_name or payload.email.split("@")[0],
                "created_at": datetime.utcnow().isoformat()
            }).execute()
        except Exception as profile_err:
            logger.warning(f"Profile creation warning: {profile_err}")

        display_name = payload.display_name or payload.email.split("@")[0]
        return AuthResponse(
            access_token=access_token,
            user=UserResponse(
                id=user_id,
                email=payload.email,
                display_name=display_name,
                name=display_name,
                createdAt=datetime.utcnow().isoformat()
            )
        )
    except Exception as e:
        err_msg = str(e)
        logger.error(f"Signup error: {err_msg}")

        # H5 Fix: dev fallback only in DEBUG mode — never silently succeed in production
        if settings.DEBUG and ("placeholder" in settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY):
            dev_id = f"user-{uuid.uuid4().hex[:8]}"
            name = payload.display_name or payload.email.split("@")[0]
            return AuthResponse(
                access_token=f"dev-jwt-token-{dev_id}",
                user=UserResponse(
                    id=dev_id,
                    email=payload.email,
                    display_name=name,
                    name=name,
                    createdAt=datetime.utcnow().isoformat()
                )
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sign up failed: {err_msg}"
        )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest):
    """
    Authenticates an existing user via Supabase Auth.
    """
    try:
        res = supabase.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password
        })
        
        user_id = str(res.user.id) if (res and res.user) else "00000000-0000-0000-0000-000000000000"
        access_token = res.session.access_token if (res and res.session) else f"dev-token-{user_id}"

        display_name = None
        if res and res.user and res.user.user_metadata:
            display_name = res.user.user_metadata.get("display_name") or res.user.user_metadata.get("full_name")
        
        if not display_name:
            try:
                prof = supabase.table("profiles").select("*").eq("id", user_id).execute()
                if prof.data and len(prof.data) > 0:
                    display_name = prof.data[0].get("display_name")
            except Exception:
                pass

        if not display_name:
            display_name = payload.email.split("@")[0]

        return AuthResponse(
            access_token=access_token,
            user=UserResponse(
                id=user_id,
                email=payload.email,
                display_name=display_name,
                name=display_name,
                createdAt=datetime.utcnow().isoformat()
            )
        )
    except Exception as e:
        err_msg = str(e)
        logger.error(f"Login error: {err_msg}")

        # H5 Fix: dev fallback only in DEBUG mode — never silently succeed in production
        if settings.DEBUG and ("placeholder" in settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY):
            dev_id = "00000000-0000-0000-0000-000000000000"
            name = payload.email.split("@")[0]
            return AuthResponse(
                access_token=f"dev-jwt-token-{dev_id}",
                user=UserResponse(
                    id=dev_id,
                    email=payload.email,
                    display_name=name,
                    name=name,
                    createdAt=datetime.utcnow().isoformat()
                )
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please check your credentials."
        )


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    try:
        supabase.auth.reset_password_for_email(payload.email)
        return {"ok": True, "message": "Password reset link sent to your email."}
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        return {"ok": True, "message": "If that email exists, a reset link was sent."}


@router.get("/me", response_model=UserResponse)
async def get_me(user_id: str = Depends(get_current_user)):
    display_name = None
    email = None
    try:
        res = supabase.table("profiles").select("*").eq("id", user_id).execute()
        if res.data and len(res.data) > 0:
            profile = res.data[0]
            display_name = profile.get("display_name")
            email = profile.get("email")
    except Exception:
        pass

    if not display_name:
        try:
            # Check user_metadata or auth user details if available
            auth_user = supabase.auth.get_user()
            if auth_user and auth_user.user and auth_user.user.user_metadata:
                display_name = auth_user.user.user_metadata.get("display_name") or auth_user.user.user_metadata.get("full_name")
                email = email or auth_user.user.email
        except Exception:
            pass

    email = email or ""
    display_name = display_name or (email.split("@")[0] if "@" in email else "FoCala User")

    return UserResponse(
        id=user_id,
        email=email,
        display_name=display_name,
        name=display_name,
        createdAt=datetime.utcnow().isoformat()
    )
