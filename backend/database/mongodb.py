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
DB_NAME = os.getenv(
    "MONGO_DB_NAME",
    "agrowmindai"
)

SERVER_SELECTION_TIMEOUT_MS = int(
    os.getenv("MONGO_TIMEOUT_MS", "5000")
)

CONNECT_TIMEOUT_MS = int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "5000"))
SOCKET_TIMEOUT_MS = int(os.getenv("MONGO_SOCKET_TIMEOUT_MS", "15000"))
MAX_POOL_SIZE = max(1, int(os.getenv("MONGO_MAX_POOL_SIZE", "10")))
MIN_POOL_SIZE = max(0, int(os.getenv("MONGO_MIN_POOL_SIZE", "0")))
MAX_IDLE_TIME_MS = int(os.getenv("MONGO_MAX_IDLE_TIME_MS", "30000"))

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
    MONGO_URL = normalize_mongo_url(os.getenv("MONGO_URL"))

    client_options = {
        "serverSelectionTimeoutMS": SERVER_SELECTION_TIMEOUT_MS,
        "connectTimeoutMS": CONNECT_TIMEOUT_MS,
        "socketTimeoutMS": SOCKET_TIMEOUT_MS,
        "maxPoolSize": MAX_POOL_SIZE,
        "minPoolSize": MIN_POOL_SIZE,
        "maxIdleTimeMS": MAX_IDLE_TIME_MS,
        "retryWrites": True,
        "appname": os.getenv("MONGO_APP_NAME", "agromind-ai-render"),
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

    logger.info("MongoDB client configured for database '%s'", DB_NAME)

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

except PyMongoError as exc:

    reason = f"MongoDB client initialization failed: {exc}"

    logger.exception(reason)

    client = None
    db = UnconfiguredDatabase(reason)


# ==========================================
# CHECK DATABASE CONNECTION
# ==========================================
async def check_database() -> None:

    if client is None:
        raise DatabaseConfigurationError(
            getattr(db, "reason", "Database is not configured properly.")
        )

    await client.admin.command("ping")

    logger.info("MongoDB ping successful")


def database_status() -> dict:
    return {
        "configured": client is not None,
        "database_name": DB_NAME,
        "server_selection_timeout_ms": SERVER_SELECTION_TIMEOUT_MS,
        "connect_timeout_ms": CONNECT_TIMEOUT_MS,
        "socket_timeout_ms": SOCKET_TIMEOUT_MS,
        "max_pool_size": MAX_POOL_SIZE,
        "min_pool_size": MIN_POOL_SIZE,
        "max_idle_time_ms": MAX_IDLE_TIME_MS,
        "dns_nameservers_configured": bool(DNS_NAMESERVERS),
        "reason": getattr(db, "reason", None) if client is None else None,
    }


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
    await db.products.create_index("stock")
    await db.products.create_index("stock_quantity")
    await db.products.create_index("reserved_quantity")
    await db.products.create_index("sold_quantity")
    await db.products.create_index("created_at")
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
    await db.orders.create_index("order_status")
    await db.orders.create_index("created_at")
    await db.orders.create_index("transaction_id", sparse=True)
    await db.orders.create_index("razorpay_order_id", unique=True, sparse=True)

    # ======================================
    # PAYMENTS
    # ======================================
    await db.payments.create_index([
        ("user_id", 1),
        ("created_at", -1)
    ])
    await db.payments.create_index("payment_id", unique=True, sparse=True)
    await db.payments.create_index("razorpay_order_id", unique=True, sparse=True)

    await db.inventory_logs.create_index([
        ("product_id", 1),
        ("created_at", -1),
    ])
    await db.inventory_logs.create_index("reason")

    await db.status_history.create_index([
        ("order_id", 1),
        ("at", 1),
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

    await db.email_otps.create_index("expires_at", expireAfterSeconds=0)
    await db.email_otps.create_index([("email", 1), ("purpose", 1), ("created_at", -1)])

    # ======================================
    # RAG CHAT HISTORY
    # ======================================
    await db.rag_chats.create_index([
        ("user_id", 1),
        ("created_at", -1),
    ])
    await db.rag_chats.create_index("created_at")

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
