import os
import logging
import shutil
import time
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Depends,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pymongo.errors import PyMongoError

# =========================
# AUTH
# =========================
from auth.routes import router as auth_router
from auth.deps import get_current_user
from auth.models import user_public
from auth.otp import email_config_status
from routes.admin import router as admin_router
from routes.marketplace import router as marketplace_router, recommended_products
from rag.api.routes import router as rag_router
from rag.services.rag_service import answer_disease_question

# =========================
# AI MODULES
# =========================
from ai.detect import detect_objects
from ai.predict import (
    predict_image,
    create_gradcam,
    model_status,
    model_loaded_status,
    ensure_configured_models,
    memory_snapshot,
)
from ai.recommendations import enrich_prediction

# =========================
# DATABASE
# =========================
from database.mongodb import check_database, database_status as mongodb_status, db, ensure_indexes

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("agromind.api")

REQUIRED_ENV_VARS = [
    "MONGO_URL",
    "JWT_SECRET",
    "RAZORPAY_KEY_ID",
    "RAZORPAY_KEY_SECRET",
    "RESEND_API_KEY",
    "EMAIL_FROM",
    "ADMIN_REGISTER_SECRET",
    "CLOUDINARY_CLOUD_NAME",
    "CLOUDINARY_API_KEY",
    "CLOUDINARY_API_SECRET",
]


def missing_required_env_vars() -> list[str]:
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
    if "ADMIN_REGISTER_SECRET" in missing and os.getenv("ADMIN_SECRET"):
        missing.remove("ADMIN_REGISTER_SECRET")
    return missing

# =========================
# APP
# =========================
app = FastAPI(
    title="AgroMind AI",
    version="2.0.0",
    description="AI-powered crop disease detection system",
)

# =========================
# STARTUP
# =========================
@app.on_event("startup")
async def startup_event():
    startup_started_at = time.perf_counter()
    logger.info("startup begin")
    memory_snapshot("startup_begin")
    logger.info("Starting AgroMind AI FastAPI backend")
    logger.info("PORT=%s", os.getenv("PORT", "8000"))
    logger.info("Allowed CORS origins=%s", ALLOWED_ORIGINS)
    logger.info("Registered routes=%s", sorted({route.path for route in app.routes}))

    missing_env = missing_required_env_vars()
    if missing_env:
        message = f"Missing required environment variables: {', '.join(missing_env)}"
        if ENVIRONMENT == "production":
            raise RuntimeError(message)
        logger.warning("%s. Local development will start, but related features may fail.", message)

    try:
        await ensure_indexes()
        logger.info("MongoDB connection OK and indexes initialized")
    except Exception as e:
        logger.exception("Database startup warning: %s", str(e))

    try:
        logger.info("Model startup artifact status=%s", ensure_configured_models())
        memory_snapshot("startup_after_model_artifact_check")
    except Exception as e:
        logger.exception("Model startup warning: %s", str(e))

    total_seconds = time.perf_counter() - startup_started_at
    logger.info("startup end")
    logger.info("total startup seconds=%.3f", total_seconds)
    memory_snapshot("startup_end")


@app.options("/{full_path:path}", include_in_schema=False)
async def preflight_handler(full_path: str):
    return JSONResponse(
        status_code=200,
        content={"ok": True}
    )

# =========================
# CORS
# =========================

def _csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [
        value.strip().rstrip("/")
        for value in raw.split(",")
        if value.strip()
    ]


ENVIRONMENT = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()
PRODUCTION_FRONTEND_ORIGINS = [
    "https://agrowmindai.vercel.app",
    "https://agromind.in",
    "https://www.agromind.in",
    "https://agromindai.in",
    "https://www.agromindai.in",
]
DEFAULT_ORIGINS = []
if ENVIRONMENT != "production":
    DEFAULT_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ]
ALLOWED_ORIGINS = sorted(set(
    DEFAULT_ORIGINS
    + PRODUCTION_FRONTEND_ORIGINS
    + _csv_env("FRONTEND_URL")
    + _csv_env("FRONTEND_ORIGIN")
    + _csv_env("FRONTEND_ORIGINS")
    + _csv_env("CORS_ORIGINS")
    + _csv_env("ALLOWED_ORIGINS")
))

logger.info("Allowed CORS origins: %s", ALLOWED_ORIGINS)

TRUSTED_HOSTS = [
    host.strip()
    for host in os.getenv("TRUSTED_HOSTS", "").split(",")
    if host.strip()
]
if not TRUSTED_HOSTS:
    TRUSTED_HOSTS = ["localhost", "127.0.0.1", "*.onrender.com"]
for url_value in [os.getenv("BACKEND_URL", ""), os.getenv("FRONTEND_URL", "")]:
    parsed = urlparse(url_value)
    if parsed.hostname and parsed.hostname not in TRUSTED_HOSTS:
        TRUSTED_HOSTS.append(parsed.hostname)


app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=TRUSTED_HOSTS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
    return response



# =========================
# ROUTERS
# =========================
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(marketplace_router)
app.include_router(admin_router)
app.include_router(rag_router)




# =========================
# PATHS
# =========================
BASE_DIR = Path(__file__).resolve().parent

UPLOAD_FOLDER = BASE_DIR / "uploads"
RESULTS_FOLDER = BASE_DIR / "results"

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
RESULTS_FOLDER.mkdir(parents=True, exist_ok=True)

app.mount(
    "/results",
    StaticFiles(directory=str(RESULTS_FOLDER)),
    name="results"
)

# =========================
# SUPPORTED CROPS
# =========================
SUPPORTED_CROPS = {
    "tomato",
    "mango",
    "coconut"
}

# =========================
# HELPERS
# =========================
def save_upload(file: UploadFile) -> str:

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file uploaded"
        )

    suffix = Path(file.filename).suffix or ".jpg"

    filename = f"{uuid4().hex}{suffix}"

    file_path = UPLOAD_FOLDER / filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return str(file_path)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


def validate_crop(crop: str):

    if crop not in SUPPORTED_CROPS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid crop",
                "supported_crops": sorted(SUPPORTED_CROPS)
            }
        )

# =========================
# GLOBAL ERROR HANDLER
# =========================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
        },
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Validation error path=%s method=%s errors=%s",
        request.url.path,
        request.method,
        exc.errors(),
    )
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception path=%s method=%s", request.url.path, request.method)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error"
        }
    )

# =========================
# ROOT
# =========================
@app.get("/", tags=["System"])
async def home():
    return {
        "success": True,
        "message": "AgroMind AI Backend Running",
        "supported_crops": sorted(SUPPORTED_CROPS)
    }

# =========================
# HEALTH
# =========================
@app.get("/health", tags=["System"])
async def health():

    models = model_status()
    database_status = "connected"
    database_details = mongodb_status()
    missing_env = missing_required_env_vars()

    try:
        await check_database()
    except Exception as exc:
        logger.exception("Health database check failed")
        database_status = "unreachable"
        database_details["reason"] = str(exc)

    missing_models = [
        crop
        for crop, status in models.items()
        if crop in SUPPORTED_CROPS
        and not status.get("available", False)
    ]

    return {
        "success": True,
        "status": "healthy" if not missing_models and database_status == "connected" else "degraded",
        "database": database_status,
        "database_details": database_details,
        "email": email_config_status(),
        "models": models,
        "missing_models": missing_models,
        "missing_env": missing_env,
    }


@app.get("/health/models", tags=["System"])
async def health_models():
    return model_loaded_status()

# =========================
# YOLO DETECT
# =========================
@app.post("/detect", tags=["AI"])
async def detect(
    file: UploadFile = File(...)
):

    file_path = save_upload(file)

    try:
        detections, result_image = detect_objects(file_path)

        return {
            "success": True,
            "filename": file.filename,
            "detections": detections,
            "result_image": result_image
        }

    except Exception as e:
        logger.exception("Detection failed file_path=%s filename=%s", file_path, file.filename)
        raise HTTPException(
            status_code=503,
            detail="Detection failed. Check backend logs for details."
        )

# =========================
# PREDICT
# =========================
@app.post("/predict/{crop}", tags=["AI"])
async def predict_crop(
    crop: str,
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):

    validate_crop(crop)

    file_path = save_upload(file)
    started_at = time.perf_counter()

    try:
        logger.info("Prediction request crop=%s user=%s file_path=%s filename=%s", crop, user.get("email"), file_path, file.filename)
        result = predict_image(file_path, crop)

        if "error" in result:
            logger.error("Prediction returned error crop=%s result=%s", crop, result)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Prediction service unavailable",
                    "reason": result.get("error"),
                    "exception_type": result.get("exception_type"),
                    "message": result.get("message"),
                }
            )

        result = enrich_prediction(crop, result)
        market_products = await recommended_products(crop, result.get("disease", ""), limit=6)
        result["marketplace_products"] = market_products
        result.setdefault("recommendation", {})["marketplace_products"] = market_products
        rag_guidance = None
        rag_error = None
        try:
            rag_guidance = await answer_disease_question(crop, result.get("disease", ""), user=user)
            result["rag_guidance"] = {
                "answer": rag_guidance["answer"],
                "sources": rag_guidance["sources"],
                "provider": rag_guidance.get("provider"),
            }
        except Exception as exc:
            rag_error = "RAG guidance is unavailable. Build the RAG index and verify LLM configuration."
            logger.exception("RAG guidance failed crop=%s disease=%s user=%s", crop, result.get("disease"), user.get("email"))
            result["rag_guidance_error"] = rag_error

        await db.prediction_history.insert_one({
            "user_id": str(user["_id"]),
            "email": user["email"],
            "crop": crop,
            "prediction": result,
            "created_at": datetime.now(timezone.utc)
        })

        return {
            "success": True,
            "crop": crop,
            "disease": result.get("disease"),
            "confidence": result.get("confidence"),
            "severity": result.get("severity"),
            "recommendation": result.get("recommendation", {}),
            "prediction": result,
            "marketplace_products": market_products,
            "rag_guidance": result.get("rag_guidance"),
            "rag_guidance_error": rag_error,
            "user": user["email"]
        }

    except HTTPException:
        raise
    except PyMongoError as e:
        logger.exception("Prediction database failure crop=%s user=%s", crop, user.get("email"))
        raise HTTPException(
            status_code=503,
            detail="Database is not reachable. Check the backend MONGO_URL and MongoDB network access."
        )
    except Exception as e:
        logger.exception("Prediction failed crop=%s user=%s file_path=%s", crop, user.get("email"), file_path)
        raise HTTPException(
            status_code=500,
            detail="Prediction failed. Check backend logs for details."
        )
    finally:
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception:
            logger.warning("Could not delete temporary prediction upload path=%s", file_path, exc_info=True)
        logger.info(
            "Prediction request finished crop=%s user=%s duration_ms=%.2f",
            crop,
            user.get("email"),
            (time.perf_counter() - started_at) * 1000,
        )

# =========================
# PROFILE
# =========================
@app.get("/profile", tags=["User"])
async def profile(
    user=Depends(get_current_user)
):
    return {
        "success": True,
        "user": user_public(user)
    }


# =========================
# HISTORY
# =========================
@app.get("/history", tags=["User"])
async def history(
    limit: int = 20,
    user=Depends(get_current_user)
):
    safe_limit = max(1, min(limit, 100))
    cursor = (
        db.prediction_history
        .find({"user_id": str(user["_id"])})
        .sort("created_at", -1)
        .limit(safe_limit)
    )
    items = []

    async for item in cursor:
        items.append({
            "id": str(item["_id"]),
            "crop": item.get("crop"),
            "prediction": item.get("prediction"),
            "created_at": item.get("created_at"),
        })

    return {
        "success": True,
        "items": items,
    }

# =========================
# MAIN
# =========================
if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
