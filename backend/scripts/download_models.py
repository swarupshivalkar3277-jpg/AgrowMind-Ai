from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("agromind.model_download")

BACKEND_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = BACKEND_DIR / "models"
MIN_MODEL_BYTES = 1024 * 1024
CHUNK_SIZE = 1024 * 1024
REQUEST_TIMEOUT_SECONDS = int(os.getenv("MODEL_DOWNLOAD_TIMEOUT_SECONDS", "120"))
MAX_ATTEMPTS = int(os.getenv("MODEL_DOWNLOAD_MAX_ATTEMPTS", "3"))

MODELS = {
    "tomato": ("TOMATO_MODEL_URL", "tomato_model.keras"),
    "mango": ("MANGO_MODEL_URL", "mango_model.keras"),
    "coconut": ("COCONUT_MODEL_URL", "coconut_model.keras"),
}


def google_drive_file_id(url: str) -> str | None:
    parsed = urlparse(url)
    query_id = parse_qs(parsed.query).get("id", [None])[0]
    if query_id:
        return query_id

    match = re.search(r"/file/d/([^/]+)", parsed.path)
    if match:
        return match.group(1)

    return None


def google_drive_confirm_token(response: requests.Response) -> str | None:
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            return value

    return None


def google_drive_confirm_token_from_html(html: str) -> str | None:
    match = re.search(r"confirm=([0-9A-Za-z_]+)", html)
    return match.group(1) if match else None


def stream_response_to_file(response: requests.Response, destination: Path) -> int:
    total = 0
    temp_path = destination.with_suffix(destination.suffix + ".part")
    with temp_path.open("wb") as file:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if not chunk:
                continue
            file.write(chunk)
            total += len(chunk)
            if total and total % (10 * CHUNK_SIZE) < CHUNK_SIZE:
                logger.info("download progress file=%s bytes=%s", destination.name, total)
    temp_path.replace(destination)
    return total


def fetch(url: str, destination: Path) -> int:
    with requests.Session() as session:
        response = session.get(url, stream=True, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()

        file_id = google_drive_file_id(url)
        token = google_drive_confirm_token(response)
        content_type = response.headers.get("content-type", "")
        if not token and file_id and "text/html" in content_type.lower():
            token = google_drive_confirm_token_from_html(response.text)

        if file_id and token:
            logger.info("Google Drive confirmation token detected file=%s", destination.name)
            response.close()
            response = session.get(
                "https://drive.google.com/uc",
                params={"export": "download", "confirm": token, "id": file_id},
                stream=True,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type.lower():
            body_preview = response.text[:500]
            raise RuntimeError(f"Download returned HTML instead of a model file: {body_preview!r}")

        return stream_response_to_file(response, destination)


def verify_model(path: Path) -> int:
    if not path.exists():
        raise FileNotFoundError(f"Model file was not created: {path}")
    size = path.stat().st_size
    if size <= MIN_MODEL_BYTES:
        raise RuntimeError(f"Model file is too small: path={path} size={size}")
    return size


def download_model(crop: str, env_name: str, filename: str) -> dict:
    url = os.getenv(env_name, "").strip()
    destination = MODEL_DIR / filename
    if not url:
        raise RuntimeError(f"{env_name} is not configured")

    logger.info("downloading %s model", crop)
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            logger.info("model download attempt crop=%s attempt=%s max_attempts=%s", crop, attempt, MAX_ATTEMPTS)
            fetch(url, destination)
            size = verify_model(destination)
            logger.info("%s model downloaded path=%s size_bytes=%s", crop, destination, size)
            return {"crop": crop, "path": str(destination), "size_bytes": size}
        except Exception as exc:
            last_error = exc
            logger.warning("model download failed crop=%s attempt=%s error=%s", crop, attempt, exc)
            if attempt < MAX_ATTEMPTS:
                time.sleep(min(2**attempt, 10))

    raise RuntimeError(f"{crop} model download failed after {MAX_ATTEMPTS} attempts: {last_error}")


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("model download directory ready path=%s", MODEL_DIR)

    results = {}
    failures = {}
    for crop, (env_name, filename) in MODELS.items():
        try:
            results[crop] = download_model(crop, env_name, filename)
        except Exception as exc:
            failures[crop] = str(exc)
            logger.error("required model download failed crop=%s error=%s", crop, exc)

    if failures:
        raise SystemExit(f"Required model downloads failed: {failures}")

    logger.info("all required models downloaded results=%s", results)


if __name__ == "__main__":
    main()
