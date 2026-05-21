import os
import logging
import shutil
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Depends,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

# =========================
# AUTH
# =========================
from auth.routes import router as auth_router
from auth.deps import get_current_user
from auth.models import user_public

# =========================
# AI MODULES
# =========================
from ai.detect import detect_objects
from ai.predict import (
    predict_image,
    create_gradcam,
    model_status,
    ensure_configured_models,
)
from ai.recommendations import enrich_prediction

# =========================
# DATABASE
# =========================
from database.mongodb import check_database, db, ensure_indexes

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("agromind.api")

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
    logger.info("Starting AgroMind AI FastAPI backend")
    logger.info("PORT=%s", os.getenv("PORT", "8000"))
    logger.info("Allowed CORS origins=%s", ALLOWED_ORIGINS)
    logger.info("Registered routes=%s", sorted({route.path for route in app.routes}))

    try:
        await ensure_indexes()
        logger.info("MongoDB connection OK and indexes initialized")
    except Exception as e:
        logger.exception("Database startup warning: %s", str(e))

    try:
        logger.info("Model startup status=%s", ensure_configured_models())
    except Exception as e:
        logger.exception("Model startup warning: %s", str(e))

# =========================
# CORS
# =========================

ALLOWED_ORIGINS = ["*"]

logger.info("Allowed CORS origins: %s", ALLOWED_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# ROUTERS
# =========================
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])


@app.options("/{full_path:path}", include_in_schema=False)
async def preflight_handler(full_path: str):
    return JSONResponse(status_code=200, content={"ok": True})

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
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc)
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

    try:
        await check_database()
    except Exception:
        database_status = "unreachable"

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
        "models": models,
        "missing_models": missing_models,
    }

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
        raise HTTPException(
            status_code=503,
            detail=f"Detection failed: {str(e)}"
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

    try:
        result = predict_image(file_path, crop)

        if "error" in result:
            raise HTTPException(
                status_code=503,
                detail=result
            )

        result = enrich_prediction(crop, result)

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
            "prediction": result,
            "severity": result.get("severity"),
            "fertilizer": result.get("fertilizer", []),
            "treatment": result.get("treatment", []),
            "irrigation": result.get("irrigation", ""),
            "prevention": result.get("prevention", []),
            "organic_solution": result.get("organic_solution", []),
            "harvest_risk": result.get("harvest_risk"),
            "user": user["email"]
        }

    except HTTPException:
        raise
    except PyMongoError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database is not reachable. Check the backend MONGO_URL and MongoDB network access: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
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
