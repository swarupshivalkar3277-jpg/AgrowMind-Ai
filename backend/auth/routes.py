from fastapi import APIRouter, Depends, HTTPException, status
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

router = APIRouter(tags=["Auth"])


def token_for_user(db_user: dict) -> dict:
    token = create_access_token({
        "sub": str(db_user["_id"]),
        "email": db_user["email"],
        "role": db_user.get("role", "user"),
    })
    return {"access_token": token, "token_type": "bearer"}


@router.post("/send-otp")
async def send_otp(payload: OtpRequest):
    await create_and_send_otp(payload.email, payload.purpose)
    return {"success": True, "message": "OTP sent to email"}


@router.post("/register", status_code=status.HTTP_201_CREATED)
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

    user_data = build_user_document(
        name=user.name,
        email=email,
        hashed_password=hash_password(user.password),
        role=user.role,
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


@router.post("/login", response_model=TokenResponse)
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
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=503, detail="GOOGLE_CLIENT_ID is not configured")

    response = requests.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"id_token": payload.id_token},
        timeout=15,
    )
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    profile = response.json()
    if profile.get("aud") != client_id or profile.get("email_verified") != "true":
        raise HTTPException(status_code=401, detail="Google token verification failed")

    email = profile["email"].lower()
    db_user = await db.users.find_one({"email": email})
    if not db_user:
        now_user = build_user_document(
            name=profile.get("name") or email.split("@")[0],
            email=email,
            hashed_password=hash_password(os.urandom(24).hex()),
            role=payload.role,
        )
        now_user["auth_provider"] = "google"
        result = await db.users.insert_one(now_user)
        db_user = await db.users.find_one({"_id": result.inserted_id})

    return token_for_user(db_user)


@router.post("/logout")
async def logout():
    return {"message": "Logged out. Remove the token on the client."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return user_public(current_user)
