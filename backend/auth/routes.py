from urllib.parse import urlencode
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pymongo.errors import PyMongoError

from auth.deps import get_current_user
import os

import requests

from auth.models import build_user_document, user_public
from auth.otp import create_and_send_otp, verify_otp
from auth.schemas import (
    ForgotPasswordReset,
    GoogleAuthRequest,
    OtpRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from auth.utils import create_access_token, hash_password, verify_password
from database.mongodb import db
from utils.rate_limit import rate_limit

router = APIRouter(tags=["Auth"])
logger = logging.getLogger("agromind.auth.routes")


def frontend_url() -> str:
    return (
        os.getenv("FRONTEND_URL")
        or os.getenv("FRONTEND_ORIGIN")
        or "https://agrowmindai.vercel.app"
    ).rstrip("/")


def token_for_user(db_user: dict) -> dict:
    token = create_access_token({
        "sub": str(db_user["_id"]),
        "email": db_user["email"],
        "role": db_user.get("role", "farmer"),
    })
    return {"access_token": token, "token_type": "bearer"}


def validate_registration_role(user: UserRegister) -> str:
    role = user.role or "farmer"
    if role != "admin":
        return "farmer"

    if not user.admin_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin secret required",
        )

    expected_secret = os.getenv("ADMIN_REGISTER_SECRET") or os.getenv("ADMIN_SECRET")
    if not expected_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin registration secret is not configured on the backend.",
        )
    if user.admin_secret != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin secret",
        )
    return "admin"


@router.post("/send-otp", dependencies=[Depends(rate_limit(5, 300))])
async def send_otp(payload: OtpRequest):
    logger.info("OTP request received email=%s purpose=%s", payload.email, payload.purpose)
    try:
        await create_and_send_otp(payload.email, payload.purpose)
    except PyMongoError as exc:
        logger.exception("OTP database failure email=%s purpose=%s", payload.email, payload.purpose)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not reachable. Check the backend MONGO_URL and MongoDB network access.",
        ) from exc
    except HTTPException:
        logger.exception("OTP request failed email=%s purpose=%s", payload.email, payload.purpose)
        raise
    return {"success": True, "message": "OTP sent to email"}


@router.post("/register", status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit(5, 300))])
async def register(user: UserRegister):
    email = user.email.lower()

    try:
        existing = await db.users.find_one({"email": email})
    except PyMongoError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not reachable. Check the backend MONGO_URL and MongoDB network access.",
        ) from exc

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    await verify_otp(email, "register", user.otp_code)
    role = validate_registration_role(user)

    user_data = build_user_document(
        name=user.name,
        email=email,
        hashed_password=hash_password(user.password),
        role=role,
    )
    try:
        result = await db.users.insert_one(user_data)
        created = await db.users.find_one({"_id": result.inserted_id})
    except PyMongoError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not reachable. Check the backend MONGO_URL and MongoDB network access.",
        ) from exc

    try:
        token = token_for_user(created)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT_SECRET_KEY is missing on the backend host.",
        ) from exc

    return {"success": True, "user": user_public(created), **token}


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit(10, 300))])
async def login(user: UserLogin):
    email = user.email.lower()

    try:
        db_user = await db.users.find_one({"email": email})
    except PyMongoError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not reachable. Check the backend MONGO_URL and MongoDB network access.",
        ) from exc

    if not db_user or not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if db_user.get("blocked"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is blocked. Contact AgroMind AI support.",
        )

    await verify_otp(email, "login", user.otp_code)

    try:
        return token_for_user(db_user)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT_SECRET_KEY is missing on the backend host.",
        ) from exc


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordReset):
    email = payload.email.lower()
    await verify_otp(email, "forgot_password", payload.otp_code)

    result = await db.users.update_one(
        {"email": email},
        {"$set": {"hashed_password": hash_password(payload.new_password)}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Email is not registered")

    return {"success": True, "message": "Password reset successfully"}


@router.post("/google", response_model=TokenResponse)
async def google_auth(payload: GoogleAuthRequest):
    logger.info(
        "Google auth request role=%s token_present=%s token_length=%s",
        payload.role,
        bool(payload.id_token),
        len(payload.id_token or ""),
    )
    profile = verify_google_id_token(payload.id_token)
    db_user = await upsert_google_user(profile, payload.role)
    try:
        return token_for_user(db_user)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT_SECRET_KEY is missing on the backend host.",
        ) from exc


def verify_google_id_token(id_token: str) -> dict:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=503, detail="GOOGLE_CLIENT_ID is not configured")

    try:
        response = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
            timeout=15,
        )
    except requests.RequestException as exc:
        logger.exception("Google tokeninfo request failed")
        raise HTTPException(status_code=502, detail="Google token verification service is unreachable") from exc

    if response.status_code != 200:
        logger.error("Google token rejected status=%s response_body=%s", response.status_code, response.text)
        raise HTTPException(status_code=401, detail="Invalid Google token")

    profile = response.json()
    if profile.get("aud") != client_id or profile.get("email_verified") != "true":
        logger.error(
            "Google token verification failed aud_match=%s email_verified=%s response_keys=%s",
            profile.get("aud") == client_id,
            profile.get("email_verified"),
            sorted(profile.keys()),
        )
        raise HTTPException(status_code=401, detail="Google token verification failed")

    logger.info("Google token verified email=%s aud_match=True", profile.get("email"))
    return profile


async def upsert_google_user(profile: dict, role: str) -> dict:
    email = profile["email"].lower()
    try:
        db_user = await db.users.find_one({"email": email})
        if not db_user:
            requested_role = role if role == "farmer" else "farmer"
            now_user = build_user_document(
                name=profile.get("name") or email.split("@")[0],
                email=email,
                hashed_password=hash_password(os.urandom(24).hex()),
                role=requested_role,
            )
            now_user["auth_provider"] = "google"
            result = await db.users.insert_one(now_user)
            db_user = await db.users.find_one({"_id": result.inserted_id})
    except PyMongoError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not reachable. Check the backend MONGO_URL and MongoDB network access.",
        ) from exc

    return db_user


@router.get("/google/callback", include_in_schema=False)
async def google_callback(
    code: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    redirect_base = f"{frontend_url()}/login"

    if error:
        return RedirectResponse(f"{redirect_base}?{urlencode({'error': error})}")

    if not code:
        return RedirectResponse(f"{redirect_base}?{urlencode({'error': 'Missing Google authorization code'})}")

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    if not client_id or not client_secret or not redirect_uri:
        return RedirectResponse(
            f"{redirect_base}?{urlencode({'error': 'Google OAuth redirect is not configured on the backend'})}"
        )

    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )

    if token_response.status_code != 200:
        return RedirectResponse(f"{redirect_base}?{urlencode({'error': 'Google authorization failed'})}")

    id_token = token_response.json().get("id_token")
    if not id_token:
        return RedirectResponse(f"{redirect_base}?{urlencode({'error': 'Google did not return an ID token'})}")

    profile = verify_google_id_token(id_token)
    db_user = await upsert_google_user(profile, "farmer")
    token = token_for_user(db_user)["access_token"]

    return RedirectResponse(f"{frontend_url()}/dashboard?{urlencode({'token': token})}")


@router.post("/logout")
async def logout():
    return {"message": "Logged out. Remove the token on the client."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return user_public(current_user)
