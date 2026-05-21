import os
import logging
from pathlib import Path

import certifi
import dns.resolver
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import InvalidURI

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logger = logging.getLogger("agromind.database")


def normalize_mongo_url(raw_url: str | None) -> str:
    if not raw_url:
        raise RuntimeError(
            "MONGO_URL is missing. Add your MongoDB Atlas connection string to "
            "Render environment variables."
        )

    url = raw_url.strip().strip("\"'")

    # Render's dashboard value field should contain only mongodb+srv://...
    # This recovers from accidentally pasting MONGO_URL=mongodb+srv://...
    if url.startswith("MONGO_URL="):
        logger.warning("MONGO_URL contains a duplicated 'MONGO_URL=' prefix; normalizing it.")
        url = url.split("=", 1)[1].strip().strip("\"'")

    if not url.startswith(("mongodb://", "mongodb+srv://")):
        raise RuntimeError(
            "Invalid MONGO_URL. It must start with mongodb:// or mongodb+srv://. "
            "In Render, set the MONGO_URL value to the URI only, without 'MONGO_URL='."
        )

    if "localhost" in url or "127.0.0.1" in url:
        raise RuntimeError(
            "MONGO_URL points to localhost. Use a MongoDB Atlas URI on Render."
        )

    return url


MONGO_URL = normalize_mongo_url(os.getenv("MONGO_URL"))
DB_NAME = os.getenv("MONGO_DB_NAME", "agromind_ai")
SERVER_SELECTION_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "5000"))
DNS_NAMESERVERS = [
    nameserver.strip()
    for nameserver in os.getenv("MONGO_DNS_NAMESERVERS", "").split(",")
    if nameserver.strip()
]


if DNS_NAMESERVERS:
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = DNS_NAMESERVERS
    dns.resolver.default_resolver = resolver

try:
    client_options = {
        "serverSelectionTimeoutMS": SERVER_SELECTION_TIMEOUT_MS,
    }

    if MONGO_URL.startswith("mongodb+srv://"):
        client_options.update({
            "tls": True,
            "tlsCAFile": certifi.where(),
        })

    client = AsyncIOMotorClient(
        MONGO_URL,
        **client_options,
    )
except InvalidURI as exc:
    raise RuntimeError(
        "Invalid MONGO_URL. URL-encode special characters in your MongoDB username or password."
    ) from exc

db = client[DB_NAME]
logger.info("MongoDB client configured for database '%s'.", DB_NAME)


async def check_database() -> None:
    await client.admin.command("ping")


async def ensure_indexes() -> None:
    await check_database()
    await db.users.create_index("email", unique=True)
    await db.prediction_history.create_index([("user_id", 1), ("created_at", -1)])
