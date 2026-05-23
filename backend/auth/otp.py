from __future__ import annotations

import os
import random
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
import httpx

from database.mongodb import db


OTP_EXPIRY_MINUTES = int(os.getenv("EMAIL_OTP_EXPIRY_MINUTES", "10"))
OTP_MIN_INTERVAL_SECONDS = int(os.getenv("EMAIL_OTP_MIN_INTERVAL_SECONDS", "60"))
OTP_MAX_PER_HOUR = int(os.getenv("EMAIL_OTP_MAX_PER_HOUR", "5"))
RESEND_ENDPOINT = "https://api.resend.com/emails"


def otp_required() -> bool:
    return os.getenv("EMAIL_OTP_REQUIRED", "true").lower() in {"1", "true", "yes", "on"}


def resend_configured() -> bool:
    return bool(os.getenv("RESEND_API_KEY") and os.getenv("EMAIL_FROM"))


def generate_otp() -> str:
    return f"{random.randint(100000, 999999)}"


async def enforce_otp_rate_limit(email: str, purpose: str) -> None:
    now = datetime.now(timezone.utc)
    recent = await db.email_otps.find_one(
        {
            "email": email.lower(),
            "purpose": purpose,
            "created_at": {"$gt": now - timedelta(seconds=OTP_MIN_INTERVAL_SECONDS)},
        },
        sort=[("created_at", -1)],
    )
    if recent:
        raise HTTPException(status_code=429, detail="Please wait before requesting another OTP")

    hourly_count = await db.email_otps.count_documents({
        "email": email.lower(),
        "purpose": purpose,
        "created_at": {"$gt": now - timedelta(hours=1)},
    })
    if hourly_count >= OTP_MAX_PER_HOUR:
        raise HTTPException(status_code=429, detail="Too many OTP requests. Try again later")


async def send_email_otp(to_email: str, code: str, purpose: str) -> None:
    if not resend_configured():
        raise HTTPException(
            status_code=503,
            detail="Resend email is not configured. Add RESEND_API_KEY and EMAIL_FROM.",
        )

    payload = {
        "from": os.getenv("EMAIL_FROM"),
        "to": [to_email],
        "subject": f"AgroMind AI OTP for {purpose.replace('_', ' ')}",
        "text": (
            f"Your AgroMind AI OTP is {code}.\n\n"
            f"This code expires in {OTP_EXPIRY_MINUTES} minutes. Do not share it with anyone."
        ),
    }
    headers = {
        "Authorization": f"Bearer {os.getenv('RESEND_API_KEY')}",
        "Content-Type": "application/json",
    }

    last_error = "Resend email request failed"
    async with httpx.AsyncClient(timeout=15) as client:
        for attempt in range(3):
            try:
                response = await client.post(RESEND_ENDPOINT, json=payload, headers=headers)
            except httpx.HTTPError as exc:
                last_error = str(exc)
            else:
                if response.status_code < 400:
                    return
                last_error = response.text

            if attempt < 2:
                continue

    raise HTTPException(status_code=502, detail=f"OTP email delivery failed: {last_error}")


async def create_and_send_otp(email: str, purpose: str) -> None:
    await enforce_otp_rate_limit(email, purpose)
    code = generate_otp()
    now = datetime.now(timezone.utc)
    await db.email_otps.insert_one({
        "email": email.lower(),
        "purpose": purpose,
        "code": code,
        "used": False,
        "expires_at": now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        "created_at": now,
    })
    await send_email_otp(email.lower(), code, purpose)


async def verify_otp(email: str, purpose: str, code: str | None) -> None:
    if not otp_required():
        return

    if not code:
        raise HTTPException(status_code=400, detail="Email OTP is required")

    now = datetime.now(timezone.utc)
    otp = await db.email_otps.find_one({
        "email": email.lower(),
        "purpose": purpose,
        "code": code,
        "used": False,
        "expires_at": {"$gt": now},
    })

    if not otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    await db.email_otps.update_one({"_id": otp["_id"]}, {"$set": {"used": True, "used_at": now}})
