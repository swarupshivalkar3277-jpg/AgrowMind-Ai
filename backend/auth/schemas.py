from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(default="user", pattern="^(user|admin|farmer|buyer|seller)$")
    otp_code: str | None = Field(default=None, min_length=4, max_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    otp_code: str | None = Field(default=None, min_length=4, max_length=8)


class OtpRequest(BaseModel):
    email: EmailStr
    purpose: str = Field(pattern="^(register|login|forgot_password)$")


class ForgotPasswordReset(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=4, max_length=8)
    new_password: str = Field(..., min_length=6, max_length=128)


class GoogleAuthRequest(BaseModel):
    id_token: str
    role: str = Field(default="user", pattern="^(user|admin|farmer|buyer|seller)$")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
