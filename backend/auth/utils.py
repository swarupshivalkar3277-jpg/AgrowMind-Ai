import os
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt as _bcrypt
from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# passlib 1.7.4 expects bcrypt.__about__.__version__, which newer bcrypt
# releases no longer expose. Supplying it avoids noisy startup/login tracebacks.
if not hasattr(_bcrypt, "__about__"):
    _bcrypt.__about__ = SimpleNamespace(
        __version__=getattr(_bcrypt, "__version__", "unknown")
    )

SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY")

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_secret_key() -> str:
    if not SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY is missing. Add JWT_SECRET_KEY or JWT_SECRET to backend/.env "
            "or your hosting environment."
        )
    return SECRET_KEY


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
