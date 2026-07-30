from pydantic import BaseModel, EmailStr
from typing import Optional

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr

class UserResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None
    name: Optional[str] = None
    avatarUrl: Optional[str] = None
    createdAt: Optional[str] = None

class AuthResponse(BaseModel):
    access_token: str
    user: UserResponse
