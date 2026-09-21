from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginStepOneResponse(BaseModel):
    temp_token: str
    mfa_required: bool
    channel: str

class OTPVerifyRequest(BaseModel):
    temp_token: str
    code: str

class UserPublic(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserPublic
