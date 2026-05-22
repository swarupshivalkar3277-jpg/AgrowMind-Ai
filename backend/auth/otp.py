from __future__ import annotations

import os
import random
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import HTTPException

from database.mongodb import db


OTP_EXPIRY_MINUTES = int(os.getenv("EMAIL_OTP_EXPIRY_MINUTES", "10"))


def otp_required() -> bool:
    return os.getenv("EMAIL_OTP_REQUIRED", "true").lower() in {"1", "true", "yes", "on"}


def smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"))


def generate_otp() -> str:
    return f"{random.randint(100000, 999999)}"


def send_email_otp(to_email: str, code: str, purpose: str) -> None:
    if not smtp_configured():
        raise HTTPException(
            status_code=503,
            detail="SMTP email is not configured. Add SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, and SMTP_FROM_EMAIL.",
        )

    sender = os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_USER")
    message = EmailMessage()
    message["Subject"] = f"AgroMind AI OTP for {purpose.replace('_', ' ')}"
    message["From"] = sender
    message["To"] = to_email
    message.set_content(
        f"Your AgroMind AI OTP is {code}.\n\n"
        f"This code expires in {OTP_EXPIRY_MINUTES} minutes. Do not share it with anyone."
    )

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() in {"1", "true", "yes", "on"}

    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=20) as server:
            server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
            server.send_message(message)


async def create_and_send_otp(email: str, purpose: str) -> None:
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
    send_email_otp(email.lower(), code, purpose)


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
