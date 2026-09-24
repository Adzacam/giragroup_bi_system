from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_token: Optional[str] = None
    remember_device: Optional[bool] = False

class UserPublic(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool

class LoginStepOneResponse(BaseModel):
    temp_token: Optional[str] = None
    mfa_required: bool
    channel: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    device_token: Optional[str] = None
    user: Optional[UserPublic] = None

class OTPVerifyRequest(BaseModel):
    temp_token: str
    code: str
    remember_device: Optional[bool] = False

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    device_token: Optional[str] = None
    user: UserPublic

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

