import os

# =========================
# PERFORMANCE / RENDER FIXES
# =========================
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_INTER_OP_THREADS"] = os.getenv("TF_INTER_OP_THREADS", "1")
os.environ["TF_INTRA_OP_THREADS"] = os.getenv("TF_INTRA_OP_THREADS", "1")
os.environ["ANONYMIZED_TELEMETRY"] = os.getenv("ANONYMIZED_TELEMETRY", "False")

import logging
import shutil
import time
import asyncio
import contextlib

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
from utils.env import env_bool

# =========================
# AUTH
# =========================
from auth.routes import router as auth_router
from auth.deps import get_current_user
from auth.models import user_public
from auth.otp import email_config_status

from routes.admin import router as admin_router
from routes.marketplace import (
    router as marketplace_router,
    recommended_products
)

from rag.api.routes import router as rag_router
from rag.services.rag_service import answer_disease_question, rag_health_status, warmup_rag

# =========================
# AI
# =========================
from ai.detect import detect_objects

from ai.predict import (
    ensure_configured_models,
    predict_image,
    preload_all_models,
    warm_prediction_pipeline,
    model_status,
    model_loaded_status,
    memory_snapshot,
)

from ai.recommendations import enrich_prediction

# =========================
# DATABASE
# =========================
from database.mongodb import (
    check_database,
    database_status as mongodb_status,
    db,
    ensure_indexes,
)

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

logger = logging.getLogger("agromind.api")

# =========================
# SETTINGS
# =========================
PREDICTION_CONCURRENCY = max(
    1,
    int(os.getenv("PREDICTION_CONCURRENCY", "1"))
)

PREDICTION_TIMEOUT_SECONDS = max(
    30,
    int(os.getenv("PREDICTION_TIMEOUT_SECONDS", "75"))
)

MODEL_PRELOAD_TIMEOUT_SECONDS = max(
    60,
    int(os.getenv("MODEL_PRELOAD_TIMEOUT_SECONDS", "240"))
)

PRELOAD_MODELS_ON_STARTUP = env_bool("PRELOAD_MODELS_ON_STARTUP", True)

PRELOAD_RAG_ON_STARTUP = env_bool("PRELOAD_RAG_ON_STARTUP")

ENABLE_RAG_GUIDANCE_ON_PREDICTION = env_bool("ENABLE_RAG_GUIDANCE_ON_PREDICTION")

RAG_PREDICTION_TIMEOUT_SECONDS = max(
    2,
    int(os.getenv("RAG_PREDICTION_TIMEOUT_SECONDS", "4"))
)

MAX_UPLOAD_BYTES = max(
    512 * 1024,
    int(os.getenv("MAX_UPLOAD_BYTES", str(8 * 1024 * 1024)))
)

UPLOAD_CHUNK_BYTES = max(
    64 * 1024,
    int(os.getenv("UPLOAD_CHUNK_BYTES", str(1024 * 1024)))
)


UPLOAD_CLEANUP_MAX_AGE_SECONDS = max(
    300,
    int(os.getenv("UPLOAD_CLEANUP_MAX_AGE_SECONDS", "1800"))
)

prediction_semaphore = asyncio.Semaphore(
    PREDICTION_CONCURRENCY
)

# =========================
# REQUIRED ENV
# =========================
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
    missing = [
        name
        for name in REQUIRED_ENV_VARS
        if not os.getenv(name)
    ]

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
# CORS
# =========================
def _csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "")

    return [
        value.strip().rstrip("/")
        for value in raw.split(",")
        if value.strip()
    ]


ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    os.getenv("ENV", "development")
).lower()

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

# =========================
# TRUSTED HOSTS
# =========================
TRUSTED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "*.onrender.com",
    "agrowmindai.vercel.app",
    "agromind.in",
    "www.agromind.in",
    "agromindai.in",
    "www.agromindai.in",
]

for host_value in _csv_env("TRUSTED_HOSTS"):
    if host_value not in TRUSTED_HOSTS:
        TRUSTED_HOSTS.append(host_value)

for url_value in [
    os.getenv("BACKEND_URL", ""),
    os.getenv("FRONTEND_URL", ""),
]:
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

# =========================
# SECURITY HEADERS
# =========================
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    return response


# =========================
# STARTUP
# =========================
@app.on_event("startup")
async def startup_event():

    startup_started_at = time.perf_counter()

    logger.info("startup begin")

    memory_snapshot("startup_begin")

    logger.info("Starting AgroMind AI backend")

    logger.info(
        "PORT=%s",
        os.getenv("PORT", "8000")
    )

    logger.info(
        "Allowed origins=%s",
        ALLOWED_ORIGINS
    )

    logger.info(
        "ENABLE_RUNTIME_MODEL_DOWNLOAD=%s",
        os.getenv("ENABLE_RUNTIME_MODEL_DOWNLOAD"),
    )

    logger.info(
        "Parsed runtime model download=%s",
        env_bool("ENABLE_RUNTIME_MODEL_DOWNLOAD"),
    )

    missing_env = missing_required_env_vars()

    if missing_env:

        message = (
            f"Missing required environment variables: "
            f"{', '.join(missing_env)}"
        )

        if ENVIRONMENT == "production":
            raise RuntimeError(message)

        logger.warning(message)

    # FAST DATABASE STARTUP
    try:
        await ensure_indexes()

        logger.info(
            "MongoDB connected and indexes initialized"
        )

    except Exception as e:
        logger.exception(
            "Database startup warning: %s",
            str(e)
        )

    model_artifacts = ensure_configured_models()
    logger.info("Model artifact startup status=%s", model_artifacts)

    if PRELOAD_MODELS_ON_STARTUP:
        try:
            preload_result = await asyncio.wait_for(
                asyncio.to_thread(
                    preload_all_models,
                    False
                ),
                timeout=MODEL_PRELOAD_TIMEOUT_SECONDS,
            )
            logger.info("Model preload complete result=%s", preload_result)

            warmup_result = await asyncio.wait_for(
                asyncio.to_thread(warm_prediction_pipeline),
                timeout=max(30, MODEL_PRELOAD_TIMEOUT_SECONDS // 2),
            )
            logger.info("Prediction pipeline warmup complete result=%s", warmup_result)

        except asyncio.TimeoutError:
            logger.exception("Model preload timed out timeout_seconds=%s", MODEL_PRELOAD_TIMEOUT_SECONDS)
            logger.warning("Continuing startup with any models already loaded")

        except Exception:
            logger.exception("Model preload failed")
    else:
        logger.warning("Model startup preload disabled by PRELOAD_MODELS_ON_STARTUP=false")

    memory_snapshot("startup_after_model_preload")

    if PRELOAD_RAG_ON_STARTUP:
        try:
            rag_warmup_result = await warmup_rag()
            logger.info("RAG startup warmup complete result=%s", rag_warmup_result)
        except asyncio.TimeoutError:
            logger.warning("RAG startup warmup timed out; assistant will use fallback until ready")
        except Exception:
            logger.exception("RAG startup warmup failed; assistant fallback remains available")
    else:
        logger.warning("RAG startup warmup disabled by PRELOAD_RAG_ON_STARTUP=false")

    memory_snapshot("startup_after_rag_warmup")

    total_seconds = time.perf_counter() - startup_started_at

    logger.info(
        "startup complete in %.2f seconds",
        total_seconds
    )

    asyncio.create_task(cleanup_uploads_loop())


# =========================
# CLEANUP TASK
# =========================
async def cleanup_uploads_loop():

    while True:

        try:
            cutoff = (
                time.time()
                - UPLOAD_CLEANUP_MAX_AGE_SECONDS
            )

            for path in UPLOAD_FOLDER.glob("*"):

                if (
                    path.is_file()
                    and path.stat().st_mtime < cutoff
                ):
                    path.unlink(missing_ok=True)

                    logger.info(
                        "Cleaned old upload=%s",
                        path
                    )

        except Exception:
            logger.warning(
                "Upload cleanup failed",
                exc_info=True
            )

        memory_snapshot("cleanup_loop")

        await asyncio.sleep(300)


# =========================
# OPTIONS / PREFLIGHT
# =========================
@app.options("/{full_path:path}", include_in_schema=False)
async def preflight_handler(full_path: str):

    return JSONResponse(
        status_code=200,
        content={"ok": True}
    )


# =========================
# ROUTERS
# =========================
app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"]
)

app.include_router(marketplace_router)
app.include_router(admin_router)
app.include_router(rag_router)

# =========================
# PATHS
# =========================
BASE_DIR = Path(__file__).resolve().parent

UPLOAD_FOLDER = BASE_DIR / "uploads"
RESULTS_FOLDER = BASE_DIR / "results"

UPLOAD_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

RESULTS_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

app.mount(
    "/results",
    StaticFiles(directory=str(RESULTS_FOLDER)),
    name="results"
)

# =========================
# CROPS
# =========================
SUPPORTED_CROPS = {
    "tomato",
    "mango",
    "coconut",
}

# =========================
# HELPERS
# =========================
async def save_upload(file: UploadFile) -> str:

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file uploaded"
        )

    content_type = (file.content_type or "").lower()
    if content_type and not content_type.startswith("image/"):
        raise HTTPException(
            status_code=415,
            detail="Only image uploads are supported"
        )

    suffix = Path(file.filename).suffix.lower() or ".jpg"
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image format. Use JPG, PNG, or WebP."
        )

    filename = f"{uuid4().hex}{suffix}"

    file_path = UPLOAD_FOLDER / filename

    try:
        total_bytes = 0
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Image is too large. Maximum allowed size is {MAX_UPLOAD_BYTES // 1024 // 1024} MB."
                    )
                buffer.write(chunk)

        return str(file_path)

    except HTTPException:
        with contextlib.suppress(Exception):
            file_path.unlink(missing_ok=True)
        raise

    except Exception as e:
        logger.exception("Upload failed filename=%s content_type=%s", file.filename, file.content_type)

        raise HTTPException(
            status_code=500,
            detail="Upload failed"
        )
    finally:
        with contextlib.suppress(Exception):
            await file.close()


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
# ERROR HANDLERS
# =========================
@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException
):

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):

    logger.warning(
        "Validation error path=%s errors=%s",
        request.url.path,
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
async def global_exception_handler(
    request: Request,
    exc: Exception
):

    logger.exception(
        "Unhandled exception path=%s",
        request.url.path
    )

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

        logger.exception(
            "Health database check failed"
        )

        database_status = "unreachable"

        database_details["reason"] = str(exc)

    return {
        "success": True,
        "status": "healthy",
        "database": database_status,
        "database_details": database_details,
        "email": email_config_status(),
        "models": models,
        "missing_env": missing_env,
        "memory": memory_snapshot("health"),
    }


@app.get("/health/models", tags=["System"])
async def health_models():
    runtime = model_loaded_status()
    return {
        "success": True,
        "artifacts": model_status(),
        "runtime": runtime,
        "loaded_models": runtime.get("loaded_models", []),
        "missing_models": runtime.get("missing_models", []),
        "model_paths": runtime.get("model_paths", {}),
        "preload_status": runtime.get("preload_status", {}),
        "memory": memory_snapshot("health_models"),
    }


@app.get("/health/database", tags=["System"])
async def health_database():
    details = mongodb_status()
    try:
        await check_database()
        return {
            "success": True,
            "status": "connected",
            "details": details,
        }
    except Exception as exc:
        logger.exception("Database health failed")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "status": "unreachable",
                "details": {**details, "reason": str(exc)},
            },
        )


@app.get("/health/rag", tags=["System"])
async def health_rag():
    status_payload = await rag_health_status()
    status_code = 200 if status_payload.get("ready") else 503
    return JSONResponse(status_code=status_code, content=status_payload)


@app.get("/ready", tags=["System"])
async def readiness():
    models = model_loaded_status()
    missing_models = models.get("missing_models", [])

    database_ok = True
    database_error = None
    try:
        await check_database()
    except Exception as exc:
        database_ok = False
        database_error = str(exc)

    ready = database_ok
    status_code = 200 if ready else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "success": ready,
            "ready": ready,
            "database_ok": database_ok,
            "database_error": database_error,
            "missing_models": missing_models,
            "models": models,
            "memory": memory_snapshot("ready"),
        },
    )


# =========================
# DETECT
# =========================
@app.post("/detect", tags=["AI"])
async def detect(
    file: UploadFile = File(...)
):

    file_path = await save_upload(file)

    try:

        detections, result_image = detect_objects(
            file_path
        )

        return {
            "success": True,
            "filename": file.filename,
            "detections": detections,
            "result_image": result_image,
        }

    except Exception:

        logger.exception(
            "Detection failed"
        )

        raise HTTPException(
            status_code=503,
            detail="Detection failed"
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

    file_path = await save_upload(file)

    started_at = time.perf_counter()

    try:

        logger.info(
            "Prediction crop=%s user=%s",
            crop,
            user.get("email")
        )

        async with prediction_semaphore:

            result = await asyncio.wait_for(
                asyncio.to_thread(
                    predict_image,
                    file_path,
                    crop
                ),
                timeout=PREDICTION_TIMEOUT_SECONDS,
            )

        if "error" in result:

            raise HTTPException(
                status_code=503,
                detail=result
            )

        result = enrich_prediction(
            crop,
            result
        )

        try:
            market_products = await recommended_products(
                crop,
                result.get("disease", ""),
                limit=6
            )
        except Exception:
            logger.exception("Marketplace recommendation lookup failed crop=%s disease=%s", crop, result.get("disease", ""))
            market_products = []

        result["marketplace_products"] = market_products

        # OPTIONAL RAG
        if ENABLE_RAG_GUIDANCE_ON_PREDICTION:
            try:

                rag_guidance = await asyncio.wait_for(
                    answer_disease_question(
                        crop,
                        result.get("disease", ""),
                        user=user
                    ),
                    timeout=RAG_PREDICTION_TIMEOUT_SECONDS,
                )

                result["rag_guidance"] = rag_guidance

            except Exception:

                logger.exception(
                    "RAG guidance failed"
                )
                result["rag_guidance"] = {
                    "answer": "Assistant guidance is temporarily unavailable. Use the disease recommendation shown with this prediction.",
                    "sources": [],
                    "provider": "prediction_fallback",
                }
        else:
            result["rag_guidance"] = {
                "answer": "Assistant guidance is available from the AI assistant page.",
                "sources": [],
                "provider": "prediction_rag_disabled",
            }

        try:
            await db.prediction_history.insert_one({
                "user_id": str(user["_id"]),
                "email": user["email"],
                "crop": crop,
                "prediction": result,
                "created_at": datetime.now(timezone.utc)
            })
            result["history_saved"] = True
        except PyMongoError:
            logger.exception("Prediction history insert failed user=%s crop=%s", user.get("email"), crop)
            result["history_saved"] = False

        return {
            "success": True,
            "crop": crop,
            "prediction": result,
            "user": user["email"]
        }

    except asyncio.TimeoutError:

        raise HTTPException(
            status_code=504,
            detail="Prediction timed out"
        )

    except PyMongoError:

        raise HTTPException(
            status_code=503,
            detail="Database unavailable"
        )

    except HTTPException:
        raise

    except Exception:

        logger.exception(
            "Prediction failed"
        )

        raise HTTPException(
            status_code=500,
            detail="Prediction failed"
        )

    finally:

        try:
            Path(file_path).unlink(
                missing_ok=True
            )

        except Exception:
            logger.warning(
                "Failed deleting temp upload"
            )

        logger.info(
            "Prediction completed in %.2f ms",
            (time.perf_counter() - started_at) * 1000
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

    safe_limit = max(
        1,
        min(limit, 100)
    )

    cursor = (
        db.prediction_history
        .find({
            "user_id": str(user["_id"])
        })
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
        port=int(os.getenv("PORT", "8000")),
        reload=False
    )
