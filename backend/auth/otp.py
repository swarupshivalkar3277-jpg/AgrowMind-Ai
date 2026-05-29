from __future__ import annotations

import os
import random
import asyncio
import logging
import json
from email.utils import parseaddr
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
import httpx

from database.mongodb import db
from utils.env import env_bool


OTP_EXPIRY_MINUTES = int(os.getenv("EMAIL_OTP_EXPIRY_MINUTES", "10"))
OTP_MIN_INTERVAL_SECONDS = int(os.getenv("EMAIL_OTP_MIN_INTERVAL_SECONDS", "60"))
OTP_MAX_PER_HOUR = int(os.getenv("EMAIL_OTP_MAX_PER_HOUR", "5"))
RESEND_ENDPOINT = "https://api.resend.com/emails"
RESEND_TIMEOUT_SECONDS = float(os.getenv("RESEND_TIMEOUT_SECONDS", "15"))
RESEND_MAX_ATTEMPTS = int(os.getenv("RESEND_MAX_ATTEMPTS", "3"))
logger = logging.getLogger("agromind.auth.otp")


def otp_required() -> bool:
    return env_bool("EMAIL_OTP_REQUIRED", True)


def is_production() -> bool:
    return os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower() == "production"


def dev_email_fallback_enabled() -> bool:
    return (
        not is_production()
        and env_bool("EMAIL_OTP_DEV_FALLBACK")
    )


def resend_configured() -> bool:
    return bool(os.getenv("RESEND_API_KEY") and os.getenv("EMAIL_FROM"))


def email_config_status() -> dict:
    email_from = os.getenv("EMAIL_FROM", "").strip()
    parsed_name, parsed_email = parseaddr(email_from)
    from_valid = bool(parsed_email and "@" in parsed_email and "." in parsed_email.rsplit("@", 1)[-1])

    return {
        "resend_api_key_present": bool(os.getenv("RESEND_API_KEY")),
        "email_from_present": bool(email_from),
        "email_from_valid": from_valid,
        "email_from_domain": parsed_email.rsplit("@", 1)[-1] if from_valid else None,
        "otp_required": otp_required(),
        "dev_email_fallback_enabled": dev_email_fallback_enabled(),
        "resend_timeout_seconds": RESEND_TIMEOUT_SECONDS,
        "resend_max_attempts": RESEND_MAX_ATTEMPTS,
    }


def validate_resend_config() -> tuple[str, str]:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    email_from = os.getenv("EMAIL_FROM", "").strip()

    missing = []
    if not api_key:
        missing.append("RESEND_API_KEY")
    if not email_from:
        missing.append("EMAIL_FROM")
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Email service is not configured. Missing: {', '.join(missing)}.",
        )

    parsed_name, parsed_email = parseaddr(email_from)
    if not parsed_email or "@" not in parsed_email or "." not in parsed_email.rsplit("@", 1)[-1]:
        raise HTTPException(
            status_code=503,
            detail="EMAIL_FROM is invalid. Use a verified sender like AgroMind AI <otp@yourdomain.com>.",
        )

    return api_key, email_from


def generate_otp() -> str:
    return f"{random.randint(100000, 999999)}"


async def enforce_otp_rate_limit(email: str, purpose: str) -> None:
    now = datetime.now(timezone.utc)
    recent = await db.email_otps.find_one(
        {
            "email": email.lower(),
            "purpose": purpose,
            "delivery_status": "sent",
            "created_at": {"$gt": now - timedelta(seconds=OTP_MIN_INTERVAL_SECONDS)},
        },
        sort=[("created_at", -1)],
    )
    if recent:
        raise HTTPException(status_code=429, detail="Please wait before requesting another OTP")

    hourly_count = await db.email_otps.count_documents({
        "email": email.lower(),
        "purpose": purpose,
        "delivery_status": "sent",
        "created_at": {"$gt": now - timedelta(hours=1)},
    })
    if hourly_count >= OTP_MAX_PER_HOUR:
        raise HTTPException(status_code=429, detail="Too many OTP requests. Try again later")


def resend_error_message(response: httpx.Response) -> str:
    try:
        data = response.json()
    except json.JSONDecodeError:
        return response.text[:500]

    message = data.get("message") or data.get("error") or response.text
    return str(message)[:500]


async def send_email_otp(to_email: str, code: str, purpose: str) -> None:
    api_key, email_from = validate_resend_config()

    payload = {
        "from": email_from,
        "to": [to_email],
        "subject": f"AgroMind AI OTP for {purpose.replace('_', ' ')}",
        "text": (
            f"Your AgroMind AI OTP is {code}.\n\n"
            f"This code expires in {OTP_EXPIRY_MINUTES} minutes. Do not share it with anyone."
        ),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error = "Resend email request failed"
    async with httpx.AsyncClient(timeout=RESEND_TIMEOUT_SECONDS) as client:
        for attempt in range(1, RESEND_MAX_ATTEMPTS + 1):
            try:
                logger.info("Sending OTP email through Resend to=%s purpose=%s attempt=%s", to_email, purpose, attempt)
                response = await client.post(RESEND_ENDPOINT, json=payload, headers=headers)
            except httpx.TimeoutException as exc:
                last_error = f"Resend request timed out after {RESEND_TIMEOUT_SECONDS}s"
                logger.exception("Resend OTP timeout to=%s purpose=%s attempt=%s", to_email, purpose, attempt)
            except httpx.HTTPError as exc:
                last_error = str(exc)
                logger.exception("Resend OTP HTTP error to=%s purpose=%s attempt=%s", to_email, purpose, attempt)
            else:
                if response.status_code < 400:
                    logger.info("Resend OTP accepted status=%s to=%s purpose=%s", response.status_code, to_email, purpose)
                    return
                last_error = response.text
                logger.error(
                    "Resend OTP failed status=%s to=%s purpose=%s response_body=%s",
                    response.status_code,
                    to_email,
                    purpose,
                    response.text,
                )
                if response.status_code in {400, 401, 403}:
                    provider_message = resend_error_message(response)
                    raise HTTPException(
                        status_code=502,
                        detail=f"OTP email delivery failed: {provider_message}",
                    )

            if attempt < RESEND_MAX_ATTEMPTS:
                await asyncio.sleep(min(2 ** (attempt - 1), 5))

    logger.error("Resend OTP exhausted retries to=%s purpose=%s last_error=%s", to_email, purpose, last_error)
    raise HTTPException(status_code=502, detail="OTP email delivery failed. Check backend email provider logs.")


async def create_and_send_otp(email: str, purpose: str) -> None:
    await enforce_otp_rate_limit(email, purpose)
    code = generate_otp()
    now = datetime.now(timezone.utc)
    result = await db.email_otps.insert_one({
        "email": email.lower(),
        "purpose": purpose,
        "code": code,
        "used": False,
        "delivery_status": "pending",
        "expires_at": now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        "created_at": now,
    })
    logger.info(
        "OTP record created email=%s purpose=%s otp_id=%s delivery_status=pending expires_at=%s",
        email.lower(),
        purpose,
        result.inserted_id,
        now + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )
    try:
        await send_email_otp(email.lower(), code, purpose)
    except HTTPException as exc:
        if dev_email_fallback_enabled():
            logger.warning(
                "EMAIL_OTP_DEV_FALLBACK is enabled. OTP email was not delivered; use logged OTP locally. "
                "email=%s purpose=%s code=%s provider_error=%s",
                email.lower(),
                purpose,
                code,
                exc.detail,
            )
            await db.email_otps.update_one(
                {"_id": result.inserted_id},
                {
                    "$set": {
                        "delivery_status": "sent",
                        "delivery_channel": "dev_log",
                        "sent_at": datetime.now(timezone.utc),
                    }
                },
            )
            logger.warning(
                "OTP delivery marked sent through dev fallback email=%s purpose=%s otp_id=%s",
                email.lower(),
                purpose,
                result.inserted_id,
            )
            return
        await db.email_otps.delete_one({"_id": result.inserted_id})
        logger.warning(
            "OTP record deleted after provider failure email=%s purpose=%s otp_id=%s detail=%s",
            email.lower(),
            purpose,
            result.inserted_id,
            exc.detail,
        )
        raise
    except Exception:
        await db.email_otps.delete_one({"_id": result.inserted_id})
        logger.exception(
            "OTP record deleted after unexpected failure email=%s purpose=%s otp_id=%s",
            email.lower(),
            purpose,
            result.inserted_id,
        )
        raise

    await db.email_otps.update_one(
        {"_id": result.inserted_id},
        {"$set": {"delivery_status": "sent", "delivery_channel": "resend", "sent_at": datetime.now(timezone.utc)}},
    )
    logger.info(
        "OTP delivery marked sent email=%s purpose=%s otp_id=%s delivery_channel=resend",
        email.lower(),
        purpose,
        result.inserted_id,
    )


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
