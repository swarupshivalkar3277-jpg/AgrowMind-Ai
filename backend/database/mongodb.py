import os
import logging
from pathlib import Path

import certifi
import dns.resolver
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import InvalidURI, PyMongoError

# ==========================================
# LOAD ENV VARIABLES
# ==========================================
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logger = logging.getLogger("agromind.database")
logging.basicConfig(level=logging.INFO)


# ==========================================
# CUSTOM ERRORS
# ==========================================
class DatabaseConfigurationError(PyMongoError):
    pass


class UnconfiguredDatabase:
    def __init__(self, reason: str):
        self.reason = reason

    def __getattr__(self, name: str):
        raise DatabaseConfigurationError(self.reason)


# ==========================================
# NORMALIZE MONGO URL
# ==========================================
def normalize_mongo_url(raw_url: str | None) -> str:

    if not raw_url:
        raise RuntimeError(
            "MONGO_URL is missing. "
            "Add MongoDB Atlas connection string."
        )

    url = raw_url.strip().strip("\"'")

    # Fix accidental:
    # MONGO_URL=mongodb+srv://...
    if url.startswith("MONGO_URL="):
        logger.warning(
            "Detected duplicated MONGO_URL prefix. Fixing automatically."
        )
        url = url.split("=", 1)[1].strip()

    if not url.startswith(("mongodb://", "mongodb+srv://")):
        raise RuntimeError(
            "Invalid MongoDB URL format."
        )

    if "localhost" in url or "127.0.0.1" in url:
        raise RuntimeError(
            "Render cannot connect to localhost MongoDB. "
            "Use MongoDB Atlas."
        )

    return url


# ==========================================
# DATABASE CONFIG
# ==========================================
MONGO_URL = normalize_mongo_url(os.getenv("MONGO_URL"))

DB_NAME = os.getenv(
    "MONGO_DB_NAME",
    "agrowmindai"
)

SERVER_SELECTION_TIMEOUT_MS = int(
    os.getenv("MONGO_TIMEOUT_MS", "5000")
)

DNS_NAMESERVERS = [
    nameserver.strip()
    for nameserver in os.getenv(
        "MONGO_DNS_NAMESERVERS",
        ""
    ).split(",")
    if nameserver.strip()
]


# ==========================================
# CUSTOM DNS RESOLVER
# ==========================================
if DNS_NAMESERVERS:
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = DNS_NAMESERVERS
    dns.resolver.default_resolver = resolver


# ==========================================
# CONNECT TO DATABASE
# ==========================================
try:

    client_options = {
        "serverSelectionTimeoutMS": SERVER_SELECTION_TIMEOUT_MS,
    }

    # Enable TLS for Atlas
    if MONGO_URL.startswith("mongodb+srv://"):
        client_options.update({
            "tls": True,
            "tlsCAFile": certifi.where(),
        })

    client = AsyncIOMotorClient(
        MONGO_URL,
        **client_options
    )

    db = client[DB_NAME]

    logger.info(
        "MongoDB connected successfully to database '%s'",
        DB_NAME
    )

except InvalidURI:

    reason = (
        "Invalid MongoDB URI. "
        "Check username/password special characters."
    )

    logger.exception(reason)

    client = None
    db = UnconfiguredDatabase(reason)

except RuntimeError as exc:

    reason = str(exc)

    logger.warning(
        "MongoDB configuration error: %s",
        reason
    )

    client = None
    db = UnconfiguredDatabase(reason)


# ==========================================
# CHECK DATABASE CONNECTION
# ==========================================
async def check_database() -> None:

    if client is None:
        raise DatabaseConfigurationError(
            "Database is not configured properly."
        )

    await client.admin.command("ping")

    logger.info("MongoDB ping successful")


# ==========================================
# CREATE DATABASE INDEXES
# ==========================================
async def ensure_indexes() -> None:

    await check_database()
    await drop_parallel_array_product_indexes()

    # ======================================
    # USERS
    # ======================================
    await db.users.create_index(
        "email",
        unique=True
    )

    # ======================================
    # PREDICTION HISTORY
    # ======================================
    await db.prediction_history.create_index([
        ("user_id", 1),
        ("created_at", -1)
    ])

    # ======================================
    # PRODUCTS
    # IMPORTANT:
    # Separate indexes for array fields
    # ======================================
    await db.products.create_index("category")
    await db.products.create_index("crop_type")
    await db.products.create_index("disease_tags")
    await db.products.create_index("name")

    # ======================================
    # CARTS
    # ======================================
    await db.carts.create_index(
        "user_id",
        unique=True
    )

    # ======================================
    # ORDERS
    # ======================================
    await db.orders.create_index([
        ("user_id", 1),
        ("created_at", -1)
    ])

    # ======================================
    # PAYMENTS
    # ======================================
    await db.payments.create_index([
        ("user_id", 1),
        ("created_at", -1)
    ])

    # ======================================
    # WISHLIST
    # ======================================
    await db.wishlist.create_index([
        ("user_id", 1),
        ("product_id", 1)
    ], unique=True)

    # ======================================
    # RECOMMENDATIONS
    # ======================================
    await db.recommendations.create_index([
        ("crop", 1),
        ("disease", 1)
    ], unique=True)

    logger.info("All MongoDB indexes created successfully")


async def drop_parallel_array_product_indexes() -> None:
    """Remove old product indexes that combined crop_type and disease_tags arrays."""
    try:
        indexes = await db.products.index_information()
    except PyMongoError:
        return

    for index_name, index in indexes.items():
        keys = [key for key, _direction in index.get("key", [])]
        if "crop_type" in keys and "disease_tags" in keys:
            logger.warning("Dropping invalid parallel-array product index: %s", index_name)
            await db.products.drop_index(index_name)
