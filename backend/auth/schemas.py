from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(default="farmer", pattern="^(farmer|admin)$")
    otp_code: str | None = Field(default=None, min_length=4, max_length=8)
    admin_secret: str | None = Field(default=None, max_length=256)

    @field_validator("admin_secret", mode="before")
    @classmethod
    def blank_admin_secret_is_missing(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value


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
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id_token: str = Field(
        ...,
        min_length=10,
        validation_alias=AliasChoices("id_token", "credential"),
        description="Google ID token. Frontend Google Identity Services calls this response.credential.",
    )
    role: str = Field(default="farmer", pattern="^(farmer|admin)$")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
