from __future__ import annotations

import gc
import json
import logging
import os
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_INTER_OP_THREADS", "1")
os.environ.setdefault("TF_INTRA_OP_THREADS", "1")

import numpy as np
import psutil
from PIL import Image, UnidentifiedImageError

from ai.recommendations import recommendation_for, validate_recommendation_coverage
from scripts.download_models import download_model
from utils.env import env_bool


logger = logging.getLogger("agromind.ai.predict")
BASE_DIR = Path(__file__).resolve().parents[1]
TRAINING_DIR = BASE_DIR / "training"
CLASS_NAMES_DIR = TRAINING_DIR / "class_names"
MODEL_DIR = BASE_DIR / "models"


def _model_dir_from_env(value: str) -> Path:
    path = Path(value.strip()).expanduser()
    return path if path.is_absolute() else BASE_DIR / path


def _model_path_from_env(value: str) -> Path:
    path = Path(value.strip()).expanduser()
    return path if path.is_absolute() else BASE_DIR / path


MODEL_DIRS = [_model_dir_from_env(path) for path in os.getenv("MODEL_DIRS", "").split(os.pathsep) if path.strip()] or [MODEL_DIR]
IMG_SIZE = 224
SUPPORTED_CROPS = ("tomato", "mango", "coconut")
PREPROCESSING_MODES = {
    "internal_rescaling",
    "zero_to_one",
    "mobilenet_minus1_to_1",
    "uint8",
}

# These TFLite models were exported from the Keras architecture in
# train_model.py, which contains the MobileNetV2 Rescaling layer inside the
# graph. Inference must therefore feed raw RGB pixel values, not a second
# externally normalized tensor.
PREPROCESSING = {
    "tomato": {
        "mode": "internal_rescaling",
        "method": "internal_rescaling_only",
    },
    "mango": {
        "mode": "internal_rescaling",
        "method": "internal_rescaling_only",
    },
    "coconut": {
        "mode": "internal_rescaling",
        "method": "internal_rescaling_only",
    },
}

loaded_models = OrderedDict()
model_locks = {crop: threading.Lock() for crop in SUPPORTED_CROPS}
prediction_locks = {crop: threading.Lock() for crop in SUPPORTED_CROPS}
MIN_MODEL_BYTES = 1024 * 1024
MAX_LOADED_MODELS = max(1, int(os.getenv("MAX_LOADED_MODELS", str(len(SUPPORTED_CROPS)))))
UNLOAD_MODEL_AFTER_PREDICTION = env_bool("UNLOAD_MODEL_AFTER_PREDICTION")
MODEL_IDLE_UNLOAD_SECONDS = max(0, int(os.getenv("MODEL_IDLE_UNLOAD_SECONDS", "900")))
model_load_timings: dict[str, float] = {}
model_load_errors: dict[str, dict] = {}
preload_completed_at: float | None = None

_tflite_interpreter_class = None
_tflite_runtime_name: str | None = None
_artifact_details_cache: dict[tuple[str, float, int], dict[str, Any]] = {}


def memory_snapshot(label: str, **extra) -> dict:
    process = psutil.Process(os.getpid())
    memory = process.memory_info()
    snapshot = {
        "label": label,
        "rss_mb": round(memory.rss / 1024 / 1024, 2),
        "vms_mb": round(memory.vms / 1024 / 1024, 2),
        "loaded_models": list(loaded_models.keys()),
        **extra,
    }
    logger.info("Memory snapshot %s", snapshot)
    return snapshot


def get_tflite_interpreter_class():
    global _tflite_interpreter_class, _tflite_runtime_name

    if _tflite_interpreter_class is not None:
        return _tflite_interpreter_class

    try:
        from ai_edge_litert.interpreter import Interpreter

        _tflite_interpreter_class = Interpreter
        _tflite_runtime_name = "ai_edge_litert"
    except ImportError as litert_error:
        try:
            import tflite_runtime.interpreter as tflite

            _tflite_interpreter_class = tflite.Interpreter
            _tflite_runtime_name = "tflite_runtime"
        except ImportError:
            try:
                import tensorflow as tensorflow_module

                _tflite_interpreter_class = tensorflow_module.lite.Interpreter
                _tflite_runtime_name = "tensorflow.lite"
            except ImportError as tensorflow_error:
                raise RuntimeError(
                    "TensorFlow Lite runtime is not installed. Install ai-edge-litert "
                    "for production inference, or tensorflow-cpu as a local fallback."
                ) from tensorflow_error
        except Exception:
            raise
        finally:
            if _tflite_interpreter_class is None:
                logger.debug("ai-edge-litert import failed", exc_info=litert_error)

    logger.info("TensorFlow Lite runtime ready runtime=%s", _tflite_runtime_name)
    memory_snapshot("tflite_runtime_imported", runtime=_tflite_runtime_name)
    return _tflite_interpreter_class


def _shape_from_detail(detail: dict) -> tuple[int, ...] | None:
    shape = detail.get("shape")
    if shape is None:
        return None
    return tuple(int(dim) for dim in np.asarray(shape).tolist())


def _shape_text(shape: tuple[int, ...] | None) -> str | None:
    return str(shape) if shape else None


def _details_shape_text(details: list[dict]) -> str | None:
    return _shape_text(_shape_from_detail(details[0])) if details else None


def _quantization_text(detail: dict) -> str:
    quantization = detail.get("quantization", None)
    params = detail.get("quantization_parameters", {}) or {}
    scales = params.get("scales")
    zero_points = params.get("zero_points")
    if scales is not None and len(scales):
        return f"scales={np.asarray(scales).tolist()} zero_points={np.asarray(zero_points).tolist()}"
    return str(quantization)


def _output_size_from_details(output_details: list[dict]) -> int | None:
    if not output_details:
        return None

    shape = _shape_from_detail(output_details[0])
    if not shape:
        return None
    if len(shape) == 1:
        return int(shape[0])

    known_dims = [dim for dim in shape[1:] if dim > 0]
    if not known_dims:
        return None
    return int(np.prod(known_dims))


def input_shape_from_interpreter(interpreter) -> tuple[int, ...] | None:
    return _shape_from_detail(interpreter.get_input_details()[0])


def output_shape_from_interpreter(interpreter) -> tuple[int, ...] | None:
    return _shape_from_detail(interpreter.get_output_details()[0])


def output_size_from_interpreter(interpreter) -> int | None:
    return _output_size_from_details(interpreter.get_output_details())


def _interpreter_num_threads() -> int:
    try:
        return max(1, int(os.getenv("TFLITE_NUM_THREADS", os.getenv("TF_INTRA_OP_THREADS", "1"))))
    except ValueError:
        return 1


def load_tflite_model(model_path):
    path = Path(model_path)
    if not path.exists():
        logger.error("TFLite model file missing path=%s", path)
        raise FileNotFoundError(f"TFLite model file not found: {path}")

    Interpreter = get_tflite_interpreter_class()
    kwargs = {"model_path": str(path), "num_threads": _interpreter_num_threads()}

    try:
        interpreter = Interpreter(**kwargs)
    except TypeError:
        kwargs.pop("num_threads", None)
        interpreter = Interpreter(**kwargs)

    try:
        interpreter.allocate_tensors()
    except Exception as exc:
        logger.exception("TFLite tensor allocation failed path=%s", path)
        raise RuntimeError(f"TFLite tensor allocation failed for {path}: {exc}") from exc

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    logger.info(
        "TFLite model loaded path=%s runtime=%s input_shape=%s input_dtype=%s input_quantization=%s output_shape=%s size_bytes=%s",
        path,
        _tflite_runtime_name,
        _details_shape_text(input_details),
        input_details[0].get("dtype") if input_details else None,
        _quantization_text(input_details[0]) if input_details else None,
        _details_shape_text(output_details),
        path.stat().st_size,
    )
    return interpreter


def _prepare_input_tensor(batch: np.ndarray, input_detail: dict) -> np.ndarray:
    input_dtype = np.dtype(input_detail["dtype"])
    tensor = np.asarray(batch, dtype=np.float32)

    if np.issubdtype(input_dtype, np.floating):
        return tensor.astype(input_dtype, copy=False)

    scale, zero_point = input_detail.get("quantization", (0.0, 0))
    if scale:
        tensor = (tensor / float(scale)) + float(zero_point)

    if np.issubdtype(input_dtype, np.integer):
        limits = np.iinfo(input_dtype)
        tensor = np.clip(np.rint(tensor), limits.min, limits.max)

    return tensor.astype(input_dtype, copy=False)


def _resize_interpreter_input_if_needed(interpreter, input_detail: dict, batch_shape: tuple[int, ...]) -> tuple[list[dict], list[dict]]:
    current_shape = _shape_from_detail(input_detail)
    if current_shape == batch_shape:
        return interpreter.get_input_details(), interpreter.get_output_details()

    try:
        interpreter.resize_tensor_input(input_detail["index"], batch_shape, strict=False)
        interpreter.allocate_tensors()
    except Exception as exc:
        logger.exception(
            "TFLite input resize failed current_shape=%s batch_shape=%s",
            current_shape,
            batch_shape,
        )
        raise RuntimeError(
            f"TFLite input tensor shape {current_shape} cannot accept image batch shape {batch_shape}"
        ) from exc

    return interpreter.get_input_details(), interpreter.get_output_details()


def predict_tflite(interpreter, img):
    try:
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        if not input_details or not output_details:
            raise RuntimeError("TFLite model does not expose input/output tensors")

        batch = np.asarray(img)
        if batch.ndim == 3:
            batch = np.expand_dims(batch, axis=0)
        if batch.ndim != 4:
            raise ValueError(f"Expected image batch with 4 dimensions, got shape={batch.shape}")

        input_details, output_details = _resize_interpreter_input_if_needed(
            interpreter,
            input_details[0],
            tuple(int(dim) for dim in batch.shape),
        )
        input_detail = input_details[0]
        input_tensor = _prepare_input_tensor(batch, input_detail)

        interpreter.set_tensor(input_detail["index"], input_tensor)
        interpreter.invoke()
        prediction = interpreter.get_tensor(output_details[0]["index"])
        return np.asarray(prediction)
    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        logger.exception("TFLite inference tensor error")
        raise RuntimeError(f"TFLite inference failed: {exc}") from exc


def unload_model(crop: str, reason: str = "manual") -> None:
    removed = loaded_models.pop(crop, None)
    if not removed:
        return
    try:
        del removed["model"]
    except Exception:
        logger.debug("TFLite interpreter reference cleanup failed crop=%s", crop, exc_info=True)
    gc.collect()
    logger.info("Unloaded TFLite interpreter crop=%s reason=%s", crop, reason)
    memory_snapshot("after_model_unload", crop=crop, reason=reason)


def unload_unused_models(active_crop: str | None = None, reason: str = "unused") -> None:
    for crop in list(loaded_models.keys()):
        if crop != active_crop:
            unload_model(crop, reason=reason)


def unload_all_models(reason: str = "cleanup") -> None:
    for crop in list(loaded_models.keys()):
        unload_model(crop, reason=reason)


def evict_model_cache(except_crop: str | None = None) -> None:
    while len(loaded_models) > MAX_LOADED_MODELS:
        evict_crop = next((crop for crop in loaded_models if crop != except_crop), None)
        if evict_crop is None:
            return
        logger.info("Evicting TFLite interpreter crop=%s max_loaded_models=%s", evict_crop, MAX_LOADED_MODELS)
        unload_model(evict_crop, reason="cache_limit")


def unload_idle_models(except_crop: str | None = None) -> None:
    if MODEL_IDLE_UNLOAD_SECONDS <= 0:
        return

    now = time.time()
    for crop, entry in list(loaded_models.items()):
        if crop == except_crop:
            continue
        last_used_at = float(entry.get("last_used_at", entry.get("loaded_at", now)))
        idle_seconds = now - last_used_at
        if idle_seconds >= MODEL_IDLE_UNLOAD_SECONDS:
            logger.info(
                "Unloading idle TFLite interpreter crop=%s idle_seconds=%.2f limit=%s",
                crop,
                idle_seconds,
                MODEL_IDLE_UNLOAD_SECONDS,
            )
            unload_model(crop, reason="idle_timeout")


def candidate_model_paths(crop: str) -> list[Path]:
    paths: list[Path] = []
    for env_name in (f"MODEL_PATH_{crop.upper()}", f"{crop.upper()}_MODEL_PATH"):
        env_path = os.getenv(env_name, "").strip()
        if env_path:
            paths.append(_model_path_from_env(env_path))

    filenames = (f"{crop}_model.tflite",)
    paths.extend(model_dir / filename for model_dir in MODEL_DIRS for filename in filenames)

    unique_paths = []
    seen = set()
    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique_paths.append(path)
    return unique_paths


def model_path_for_crop(crop: str) -> Path:
    candidates = candidate_model_paths(crop)
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def configured_model_url(crop: str) -> str | None:
    crop_key = crop.upper()
    direct_url = os.getenv(f"{crop_key}_MODEL_URL")

    if direct_url:
        return direct_url.strip()

    base_url = os.getenv("MODEL_BASE_URL", "").strip().rstrip("/")
    if base_url:
        return f"{base_url}/{crop}_model.tflite"

    return None


def runtime_model_download_enabled() -> bool:
    return env_bool("ENABLE_RUNTIME_MODEL_DOWNLOAD")


def runtime_download_model(crop: str) -> Path | None:
    filename = f"{crop}_model.tflite"
    env_name = f"{crop.upper()}_MODEL_URL"

    if not runtime_model_download_enabled():
        logger.warning(
            "Runtime model download disabled crop=%s env_name=ENABLE_RUNTIME_MODEL_DOWNLOAD env_value=%s",
            crop,
            os.getenv("ENABLE_RUNTIME_MODEL_DOWNLOAD"),
        )
        return None

    try:
        result = download_model(crop, env_name, filename)
        downloaded_path = Path(result["path"])
        validate_downloaded_model_artifact(crop, downloaded_path)
        logger.info("Runtime TFLite model download complete crop=%s path=%s result=%s", crop, downloaded_path, result)
        return downloaded_path
    except Exception as exc:
        logger.warning("Runtime TFLite model download failed crop=%s env_name=%s error=%s", crop, env_name, exc)
        return None


def expected_class_count(crop: str) -> int | None:
    try:
        return len(load_class_names(crop))
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return None


def inspect_tflite_artifact(model_path: Path) -> dict[str, Any] | None:
    if not model_path or not model_path.exists():
        return None

    stat = model_path.stat()
    cache_key = (str(model_path), stat.st_mtime, stat.st_size)
    cached = _artifact_details_cache.get(cache_key)
    if cached:
        return cached

    interpreter = load_tflite_model(model_path)
    details = {
        "input_shape": input_shape_from_interpreter(interpreter),
        "output_shape": output_shape_from_interpreter(interpreter),
        "output_size": output_size_from_interpreter(interpreter),
        "runtime": _tflite_runtime_name,
    }
    _artifact_details_cache[cache_key] = details
    try:
        del interpreter
    finally:
        gc.collect()
    return details


def output_shape_from_artifact(model_path: Path) -> str | None:
    details = inspect_tflite_artifact(model_path)
    return _shape_text(details.get("output_shape")) if details else None


def output_size_from_artifact(model_path: Path) -> int | None:
    details = inspect_tflite_artifact(model_path)
    return int(details["output_size"]) if details and details.get("output_size") is not None else None


def validate_downloaded_model_artifact(crop: str, model_path: Path) -> None:
    expected_count = expected_class_count(crop)
    logger.info(
        "TFLite artifact validation crop=%s download_url=%s downloaded_file_size=%s class_count=%s",
        crop,
        configured_model_url(crop),
        model_path.stat().st_size if model_path.exists() else None,
        expected_count,
    )


def model_artifact_error(crop: str, model_path: Path) -> dict | None:
    size_bytes = model_path.stat().st_size
    if size_bytes < MIN_MODEL_BYTES:
        return {
            "error": f"{crop} model artifact is invalid",
            "crop": crop,
            "path": str(model_path),
            "size_bytes": size_bytes,
            "message": "Model file is too small to be a valid trained TFLite model.",
        }

    return None


def ensure_configured_models() -> dict[str, str]:
    results = {}
    runtime_download = runtime_model_download_enabled()

    for crop in SUPPORTED_CROPS:
        try:
            model_path = next((path for path in candidate_model_paths(crop) if path.exists()), None)
            if not model_path:
                logger.warning(
                    "TFLite startup artifact check crop=%s download_url=%s reason=model_not_found runtime_download=%s",
                    crop,
                    configured_model_url(crop),
                    runtime_download,
                )
                if runtime_download:
                    model_path = runtime_download_model(crop)

                if not model_path:
                    results[crop] = "missing:runtime_download_failed" if runtime_download else "missing:runtime_download_disabled"
                    continue

                logger.info("TFLite startup artifact downloaded crop=%s path=%s", crop, model_path)

            size_bytes = model_path.stat().st_size
            expected_count = expected_class_count(crop)
            logger.info(
                "TFLite startup artifact check crop=%s download_url=%s path=%s downloaded_file_size=%s class_count=%s",
                crop,
                configured_model_url(crop),
                model_path,
                size_bytes,
                expected_count,
            )
            if size_bytes < MIN_MODEL_BYTES:
                results[crop] = "invalid:file_too_small"
                logger.warning("TFLite startup warning crop=%s reason=file_too_small size_bytes=%s", crop, size_bytes)
                continue

            results[crop] = f"available:{model_path}"
        except Exception:
            results[crop] = "exception:RuntimeError"
            logger.exception("TFLite startup exception crop=%s", crop)
        if crop not in results:
            results[crop] = "missing"

    return results


def model_loaded_status() -> dict[str, str]:
    artifact_status = model_status()
    loaded = set(loaded_models.keys())
    missing = [
        crop
        for crop, status in artifact_status.items()
        if crop not in loaded or not status.get("available")
    ]
    return {
        "loaded_models": list(loaded_models.keys()),
        "missing_models": missing,
        "max_loaded_models": MAX_LOADED_MODELS,
        "model_idle_unload_seconds": MODEL_IDLE_UNLOAD_SECONDS,
        "unload_after_prediction": UNLOAD_MODEL_AFTER_PREDICTION,
        "preload_completed_at": preload_completed_at,
        "preload_status": {
            crop: {
                "loaded": crop in loaded,
                "available": status.get("available"),
                "path": status.get("path"),
                "warnings": status.get("warnings", []),
                "load_error": model_load_errors.get(crop),
                "load_time_ms": model_load_timings.get(crop),
                "last_used_at": loaded_models.get(crop, {}).get("last_used_at"),
                "loaded_at": loaded_models.get(crop, {}).get("loaded_at"),
                "preprocessing": loaded_models.get(crop, {}).get("metadata", {}).get("preprocessing"),
            }
            for crop, status in artifact_status.items()
        },
        "model_paths": {
            crop: status.get("path")
            for crop, status in artifact_status.items()
        },
        "load_timings_ms": model_load_timings,
        "load_errors": model_load_errors,
        "runtime": _tflite_runtime_name,
        "crops": {
            crop: "loaded" if crop in loaded_models else "not_loaded"
            for crop in SUPPORTED_CROPS
        },
    }


def model_status() -> dict:
    status = {}

    for crop in SUPPORTED_CROPS:
        candidates = candidate_model_paths(crop)
        available_path = next((path for path in candidates if path.exists()), None)
        size_bytes = available_path.stat().st_size if available_path else None
        warnings = []
        artifact_details = None
        loaded_entry = loaded_models.get(crop)

        if available_path and size_bytes is not None and size_bytes < MIN_MODEL_BYTES:
            warnings.append("model_file_is_too_small_to_be_a_valid_trained_tflite_model")

        class_metadata = []
        try:
            class_metadata = load_class_names(crop)
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            warnings.append(f"class_metadata_unavailable:{exc}")

        if loaded_entry:
            model = loaded_entry["model"]
            artifact_details = {
                "input_shape": input_shape_from_interpreter(model),
                "output_shape": output_shape_from_interpreter(model),
                "output_size": output_size_from_interpreter(model),
                "runtime": loaded_entry.get("metadata", {}).get("tflite_runtime"),
            }
        elif available_path and not warnings:
            try:
                artifact_details = inspect_tflite_artifact(available_path)
            except Exception as exc:
                logger.exception("TFLite status inspection failed crop=%s path=%s", crop, available_path)
                warnings.append(f"tflite_artifact_unavailable:{type(exc).__name__}")

        model_output_size = artifact_details.get("output_size") if artifact_details else None
        if class_metadata and model_output_size is not None and len(class_metadata) != model_output_size:
            warnings.append("model_output_size_does_not_match_class_metadata")

        status[crop] = {
            "available": available_path is not None and not warnings,
            "loaded": crop in loaded_models,
            "path": str(available_path) if available_path else None,
            "size_bytes": size_bytes,
            "download_url": configured_model_url(crop),
            "runtime_download_enabled": runtime_model_download_enabled(),
            "model_input_shape": _shape_text(artifact_details.get("input_shape")) if artifact_details else None,
            "model_output_shape": _shape_text(artifact_details.get("output_shape")) if artifact_details else None,
            "class_names_path": str(class_names_path(crop)),
            "metadata_class_count": len(class_metadata),
            "preprocessing": preprocessing_config_for_crop(crop, {"input_scale": None}),
            "warnings": warnings,
            "candidates": [str(path) for path in candidates],
        }

    return status


def metadata_paths_for_model(crop: str, model_path: Path) -> list[Path]:
    paths = [
        model_path.with_suffix(".json"),
        TRAINING_DIR / f"{crop}_model.json",
    ]
    unique_paths = []
    seen = set()
    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique_paths.append(path)
    return unique_paths


def class_names_path(crop: str) -> Path:
    return CLASS_NAMES_DIR / f"{crop}_classes.json"


def load_class_names(crop: str) -> list[str]:
    path = class_names_path(crop)
    if not path.exists():
        raise FileNotFoundError(
            f"Class metadata missing for crop '{crop}'. Expected {path}. "
            f"Retrain with train_model.py --crop {crop} or generate class metadata from the dataset."
        )

    with path.open("r", encoding="utf-8") as file:
        class_names = json.load(file)

    if isinstance(class_names, dict):
        class_names = class_names.get("class_names", [])

    if not isinstance(class_names, list) or not all(isinstance(item, str) and item.strip() for item in class_names):
        raise ValueError(f"Invalid class metadata in {path}. Expected class_names as a JSON array.")

    return class_names


def load_metadata(crop: str, model_path: Path) -> dict:
    for metadata_path in metadata_paths_for_model(crop, model_path):
        if metadata_path.exists():
            with metadata_path.open("r", encoding="utf-8") as file:
                metadata = json.load(file)
                logger.info("Loaded model metadata crop=%s path=%s metadata_path=%s", crop, model_path, metadata_path)
                return metadata

    logger.warning("Model metadata missing crop=%s model_path=%s using runtime defaults", crop, model_path)
    return {
        "crop": crop,
        "image_size": [IMG_SIZE, IMG_SIZE],
        "temperature": 1.0,
        "input_scale": "model_includes_preprocessing",
    }


def load_crop_model(crop: str):
    if crop not in SUPPORTED_CROPS:
        return None, None, {"error": "Invalid crop type"}

    model_path = model_path_for_crop(crop)
    logger.info("Resolving TFLite model crop=%s selected_path=%s", crop, model_path)
    if not model_path.exists():
        downloaded_path = runtime_download_model(crop)
        if downloaded_path:
            model_path = downloaded_path

    if not model_path.exists():
        logger.error("TFLite model file missing crop=%s selected_path=%s", crop, model_path)
        return None, None, {
            "error": f"{crop} model not found",
            "path": str(model_path),
            "candidates": [str(path) for path in candidate_model_paths(crop)],
            "hint": (
                f"Provide {crop}_model.tflite in backend/models during the Render build. "
                f"Set {crop.upper()}_MODEL_URL so scripts/download_models.py can fetch it."
            ),
        }

    modified_at = model_path.stat().st_mtime
    class_metadata_path = class_names_path(crop)
    class_metadata_modified_at = class_metadata_path.stat().st_mtime if class_metadata_path.exists() else None
    cache_entry = loaded_models.get(crop)
    artifact_error = model_artifact_error(crop, model_path)
    if artifact_error:
        logger.error("TFLite artifact validation failed crop=%s error=%s", crop, artifact_error)
        return None, None, artifact_error

    needs_load = (
        cache_entry is None
        or cache_entry["path"] != model_path
        or cache_entry["modified_at"] != modified_at
        or cache_entry.get("class_metadata_modified_at") != class_metadata_modified_at
    )
    if needs_load:
        with model_locks[crop]:
            cache_entry = loaded_models.get(crop)
            needs_load = (
                cache_entry is None
                or cache_entry["path"] != model_path
                or cache_entry["modified_at"] != modified_at
                or cache_entry.get("class_metadata_modified_at") != class_metadata_modified_at
            )
            if not needs_load:
                loaded_models.move_to_end(crop)
                entry = loaded_models[crop]
                if entry.get("crop") != crop:
                    return None, None, {
                        "error": "Model cache crop mismatch",
                        "crop": crop,
                        "cached_crop": entry.get("crop"),
                    }
                entry["last_used_at"] = time.time()
                return entry["model"], entry["metadata"], None

            return _load_crop_model_uncached(crop, model_path, modified_at, class_metadata_modified_at)
    else:
        logger.debug("Using cached TFLite interpreter crop=%s path=%s", crop, model_path)

    loaded_models.move_to_end(crop)
    entry = loaded_models[crop]
    if entry.get("crop") != crop:
        return None, None, {
            "error": "Model cache crop mismatch",
            "crop": crop,
            "cached_crop": entry.get("crop"),
        }
    entry["last_used_at"] = time.time()
    return entry["model"], entry["metadata"], None


def cached_crop_model(crop: str):
    if crop not in SUPPORTED_CROPS:
        return None, None, {"error": "Invalid crop type"}

    entry = loaded_models.get(crop)
    if not entry:
        status = model_status().get(crop, {})
        return None, None, {
            "error": f"{crop} model is not preloaded",
            "crop": crop,
            "path": status.get("path"),
            "available": status.get("available"),
            "message": (
                "This model was not loaded during startup. Check /health/models and Render build logs "
                f"for {crop.upper()}_MODEL_URL download and preload status."
            ),
        }

    loaded_models.move_to_end(crop)
    if entry.get("crop") != crop:
        return None, None, {
            "error": "Model cache crop mismatch",
            "crop": crop,
            "cached_crop": entry.get("crop"),
        }
    entry["last_used_at"] = time.time()
    return entry["model"], entry["metadata"], None


def _load_crop_model_uncached(crop: str, model_path: Path, modified_at: float, class_metadata_modified_at: float | None):
    load_started_at = time.perf_counter()
    metadata = load_metadata(crop, model_path)
    try:
        class_names = load_class_names(crop)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        logger.exception("Class metadata load failed crop=%s", crop)
        return None, None, {
            "error": "Class metadata could not be loaded",
            "crop": crop,
            "message": str(exc),
            "class_names_path": str(class_names_path(crop)),
        }

    try:
        memory_snapshot("before_tflite_model_load", crop=crop, path=str(model_path))
        logger.info("Loading TFLite model crop=%s path=%s size_bytes=%s", crop, model_path, model_path.stat().st_size)
        model = load_tflite_model(model_path)
    except FileNotFoundError as exc:
        logger.exception("TFLite model file missing crop=%s path=%s", crop, model_path)
        error = {
            "error": f"{crop} model not found",
            "path": str(model_path),
            "message": str(exc),
            "hint": "Restore a valid .tflite model file at this path or set MODEL_DIRS to a directory that contains it.",
        }
        model_load_errors[crop] = error
        return None, None, error
    except Exception as exc:
        logger.exception("TFLite model load failed crop=%s path=%s", crop, model_path)
        error = {
            "error": f"{crop} model could not be loaded",
            "path": str(model_path),
            "message": str(exc),
            "hint": "Restore a valid trained .tflite model file at this path or set MODEL_DIRS to a directory that contains it.",
        }
        model_load_errors[crop] = error
        return None, None, error

    output_size = output_size_from_interpreter(model)
    if output_size is None:
        model_output_shape = _shape_text(output_shape_from_interpreter(model))
        del model
        gc.collect()
        return None, None, {
            "error": "Model output size could not be determined",
            "crop": crop,
            "model_output_shape": model_output_shape,
            "model_path": str(model_path),
        }

    if len(class_names) != output_size:
        model_output_shape = _shape_text(output_shape_from_interpreter(model))
        del model
        gc.collect()
        memory_snapshot("after_invalid_model_unload", crop=crop, reason="output_shape_mismatch")
        return None, None, {
            "error": "Model output size does not match class metadata",
            "crop": crop,
            "class_count": len(class_names),
            "output_size": output_size,
            "model_output_shape": model_output_shape,
            "class_names_path": str(class_names_path(crop)),
            "model_path": str(model_path),
        }

    missing_recommendations = validate_recommendation_coverage(crop, class_names)
    if missing_recommendations:
        del model
        gc.collect()
        memory_snapshot("after_invalid_model_unload", crop=crop, reason="missing_recommendations")
        return None, None, {
            "error": "Recommendation mappings missing",
            "crop": crop,
            "missing_recommendations": missing_recommendations,
        }

    metadata["class_names"] = class_names
    metadata["tflite_runtime"] = _tflite_runtime_name
    metadata["tflite_input_shape"] = _shape_text(input_shape_from_interpreter(model))
    metadata["tflite_output_shape"] = _shape_text(output_shape_from_interpreter(model))
    metadata["preprocessing"] = preprocessing_config_for_crop(crop, metadata)
    loaded_models[crop] = {
        "crop": crop,
        "path": model_path,
        "modified_at": modified_at,
        "class_metadata_modified_at": class_metadata_modified_at,
        "model": model,
        "metadata": metadata,
        "loaded_at": time.time(),
        "last_used_at": time.time(),
    }
    loaded_models.move_to_end(crop)
    evict_model_cache(except_crop=crop)
    model_load_timings[crop] = round((time.perf_counter() - load_started_at) * 1000, 2)
    model_load_errors.pop(crop, None)
    logger.info(
        "TFLite interpreter cached crop=%s path=%s input_shape=%s output_shape=%s runtime=%s",
        crop,
        model_path,
        metadata["tflite_input_shape"],
        metadata["tflite_output_shape"],
        _tflite_runtime_name,
    )
    memory_snapshot("after_tflite_model_load", crop=crop, path=str(model_path))

    entry = loaded_models[crop]
    return entry["model"], entry["metadata"], None


def preload_all_models(strict: bool = False) -> dict:
    global preload_completed_at

    started_at = time.perf_counter()
    memory_snapshot("preload_models_begin")
    results: dict[str, dict] = {}

    for crop in SUPPORTED_CROPS:
        crop_started_at = time.perf_counter()
        model, metadata, error = load_crop_model(crop)
        duration_ms = round((time.perf_counter() - crop_started_at) * 1000, 2)
        if error:
            model_load_errors[crop] = error
            results[crop] = {"loaded": False, "duration_ms": duration_ms, "error": error}
            if strict:
                raise RuntimeError(f"{crop} model preload failed: {error}")
            logger.warning("TFLite model preload skipped crop=%s error=%s", crop, error)
            continue

        logger.info("%s TFLite model preloaded", crop)
        results[crop] = {
            "loaded": True,
            "duration_ms": duration_ms,
            "input_shape": metadata.get("tflite_input_shape"),
            "output_shape": metadata.get("tflite_output_shape"),
            "class_count": len(metadata.get("class_names") or []),
            "runtime": metadata.get("tflite_runtime"),
        }

    preload_completed_at = time.time()
    total_ms = round((time.perf_counter() - started_at) * 1000, 2)
    memory_snapshot("preload_models_complete", total_ms=total_ms)
    logger.info("TFLite model cache ready loaded_models=%s max_loaded_models=%s", list(loaded_models.keys()), MAX_LOADED_MODELS)
    return {"duration_ms": total_ms, "results": results, "loaded_models": list(loaded_models.keys())}


def warm_prediction_pipeline() -> dict:
    warmed: dict[str, dict] = {}
    for crop, entry in list(loaded_models.items()):
        try:
            model = entry["model"]
            metadata = entry["metadata"]
            image_size = get_model_image_size(model, metadata)
            batch = np.zeros((1, image_size[1], image_size[0], 3), dtype=np.float32)
            batch, preprocessing = apply_input_scale(batch, crop, metadata)
            log_preprocess_summary(crop, batch, preprocessing, model)
            with prediction_locks[crop]:
                started_at = time.perf_counter()
                predict_tflite(model, batch)
            warmed[crop] = {"ok": True, "duration_ms": round((time.perf_counter() - started_at) * 1000, 2)}
        except Exception as exc:
            logger.exception("TFLite prediction warmup failed crop=%s", crop)
            warmed[crop] = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
    memory_snapshot("prediction_warmup_complete")
    return warmed


def get_model_image_size(model, metadata: dict) -> tuple[int, int]:
    metadata_size = metadata.get("image_size")
    if isinstance(metadata_size, list) and len(metadata_size) == 2:
        return int(metadata_size[0]), int(metadata_size[1])

    input_shape = input_shape_from_interpreter(model)
    if input_shape and len(input_shape) >= 4:
        height = input_shape[1] if input_shape[1] > 0 else IMG_SIZE
        width = input_shape[2] if input_shape[2] > 0 else IMG_SIZE
        return int(width), int(height)

    return IMG_SIZE, IMG_SIZE


def image_to_batch(image_path: str | Path, size: tuple[int, int]) -> np.ndarray:
    logger.info("Preprocessing image path=%s target_size=%s", image_path, size)
    try:
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            image = image.resize(size, Image.Resampling.BILINEAR)
            array = np.asarray(image, dtype=np.float32)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        logger.warning("Invalid image file path=%s error=%s", image_path, exc)
        raise ValueError("Invalid image file. Upload a readable JPG, PNG, or WebP image.") from exc

    return np.expand_dims(array, axis=0)


def image_quality_score(batch: np.ndarray) -> float:
    image = np.squeeze(batch).astype(np.float32)
    contrast = float(np.std(image) / 64.0)
    brightness = float(1.0 - abs(np.mean(image) - 127.5) / 127.5)
    return round(max(0.0, min(1.0, (contrast * 0.55) + (brightness * 0.45))) * 100, 2)


def preprocessing_config_for_crop(crop: str, metadata: dict | None = None) -> dict:
    if crop not in PREPROCESSING:
        raise ValueError(f"No preprocessing config defined for crop '{crop}'")

    config = dict(PREPROCESSING[crop])
    override = os.getenv(f"{crop.upper()}_PREPROCESSING_MODE", "").strip().lower()
    if override:
        config["mode"] = override
        config["method"] = override

    mode = str(config.get("mode", "")).strip().lower()
    if mode not in PREPROCESSING_MODES:
        raise ValueError(
            f"Invalid preprocessing mode for crop '{crop}': {mode!r}. "
            f"Expected one of {sorted(PREPROCESSING_MODES)}."
        )

    input_scale = str((metadata or {}).get("input_scale", "")).lower()
    if mode != "internal_rescaling" and "model_includes" in input_scale:
        logger.warning(
            "External preprocessing requested for crop=%s mode=%s but metadata says model includes preprocessing input_scale=%s",
            crop,
            mode,
            input_scale,
        )

    return config


def apply_input_scale(batch: np.ndarray, crop: str, metadata: dict) -> tuple[np.ndarray, dict]:
    config = preprocessing_config_for_crop(crop, metadata)
    mode = config["mode"]
    tensor = np.asarray(batch, dtype=np.float32)

    if mode == "internal_rescaling":
        processed = tensor
    elif mode == "zero_to_one":
        processed = tensor / 255.0
    elif mode == "mobilenet_minus1_to_1":
        processed = (tensor / 127.5) - 1.0
    elif mode == "uint8":
        processed = np.clip(np.rint(tensor), 0, 255).astype(np.uint8)
    else:
        raise ValueError(f"Unsupported preprocessing mode for crop '{crop}': {mode}")

    info = {
        "mode": mode,
        "method": config.get("method") or mode,
        "metadata_input_scale": metadata.get("input_scale"),
    }
    return processed, info


def log_preprocess_summary(crop: str, batch: np.ndarray, preprocessing: dict, interpreter) -> None:
    input_detail = interpreter.get_input_details()[0]
    logger.info(
        "[PREPROCESS] crop=%s dtype=%s shape=%s min=%.6f max=%.6f method=%s mode=%s metadata_input_scale=%s",
        crop,
        batch.dtype,
        tuple(int(dim) for dim in batch.shape),
        float(np.min(batch)),
        float(np.max(batch)),
        preprocessing.get("method"),
        preprocessing.get("mode"),
        preprocessing.get("metadata_input_scale"),
    )
    logger.info(
        "[TFLITE_INPUT] crop=%s input_dtype=%s input_shape=%s quantization=%s",
        crop,
        input_detail.get("dtype"),
        _shape_from_detail(input_detail),
        _quantization_text(input_detail),
    )

def _softmax(scores: np.ndarray) -> np.ndarray:
    values = np.asarray(scores, dtype=np.float64)
    values = values - np.max(values)
    exp_values = np.exp(values)
    denominator = np.sum(exp_values)
    if not np.isfinite(denominator) or denominator <= 0:
        return np.full(values.shape, 1.0 / max(values.size, 1), dtype=np.float32)
    return (exp_values / denominator).astype(np.float32)


def normalize_scores(raw_scores: np.ndarray, temperature: float) -> np.ndarray:
    scores = np.asarray(raw_scores, dtype=np.float64)
    scores = np.squeeze(scores)
    if scores.ndim != 1 or scores.size == 0:
        raise ValueError(f"Prediction output must be a non-empty 1D score vector, got shape={scores.shape}")

    if not np.isclose(np.sum(scores), 1.0, atol=1e-3):
        scores = _softmax(scores / max(temperature, 1e-6))
    elif temperature and temperature != 1.0:
        scores = np.log(np.clip(scores, 1e-8, 1.0)) / temperature
        scores = _softmax(scores)

    return np.asarray(scores, dtype=np.float32)


def class_names_for_scores(crop: str, metadata: dict, scores: np.ndarray, model) -> list[str]:
    metadata_classes = metadata.get("class_names") or []
    output_size = len(scores)

    if len(metadata_classes) == output_size:
        return metadata_classes

    raise ValueError(
        "Model output size does not match class metadata: "
        f"crop={crop}, class_count={len(metadata_classes)}, output_size={output_size}, "
        f"model_output_shape={_shape_text(output_shape_from_interpreter(model))}"
    )


def confidence_notes(scores: np.ndarray) -> list[str]:
    sorted_scores = np.sort(scores)[::-1]
    top_score = float(sorted_scores[0])
    margin = float(sorted_scores[0] - sorted_scores[1]) if len(sorted_scores) > 1 else top_score

    notes = []
    if top_score < float(os.getenv("PREDICTION_CONFIDENCE_THRESHOLD", "0.60")):
        notes.append("low_confidence")
    if margin < 0.15:
        notes.append("ambiguous_top_classes")
    return notes


def predict_image(image_path, model_type):
    started_at = time.perf_counter()
    model_file = None
    try:
        logger.info("Prediction started crop=%s image_path=%s", model_type, image_path)
        memory_snapshot("before_prediction", crop=model_type)
        model, metadata, error = load_crop_model(model_type)
        if error:
            logger.error("Prediction cannot load TFLite model crop=%s error=%s", model_type, error)
            return error
        model_file = str(loaded_models[model_type]["path"])

        image_size = get_model_image_size(model, metadata)
        raw_batch = image_to_batch(image_path, image_size)
        quality = image_quality_score(raw_batch)
        batch, preprocessing = apply_input_scale(raw_batch, model_type, metadata)
        log_preprocess_summary(model_type, batch, preprocessing, model)

        logger.info(
            "Running TFLite prediction crop=%s image_size=%s class_count=%s model_output_shape=%s preprocessing_mode=%s cache_path=%s",
            model_type,
            image_size,
            len(metadata.get("class_names") or []),
            _shape_text(output_shape_from_interpreter(model)),
            preprocessing.get("mode"),
            model_file,
        )
        with prediction_locks[model_type]:
            prediction = predict_tflite(model, batch)
        raw_prediction = np.squeeze(prediction)
        scores = normalize_scores(raw_prediction, float(metadata.get("temperature", 1.0)))
        try:
            class_names = class_names_for_scores(model_type, metadata, scores, model)
        except ValueError as exc:
            error = {
                "error": "Model output size does not match class metadata",
                "crop": model_type,
                "class_count": int(len(metadata.get("class_names") or [])),
                "output_size": int(len(scores)),
                "model_output_shape": _shape_text(output_shape_from_interpreter(model)),
                "class_names_path": str(class_names_path(model_type)),
                "message": str(exc),
            }
            logger.error("Class validation failed crop=%s error=%s", model_type, error)
            return error

        predicted_index = int(np.argmax(scores))
        predicted_class = class_names[predicted_index]
        confidence = float(np.max(scores) * 100)
        top_predictions = [
            {"class_name": class_names[index], "confidence": round(float(scores[index] * 100), 2)}
            for index in np.argsort(scores)[::-1][:5]
        ]
        notes = confidence_notes(scores)
        recommendations = recommendation_for(model_type, predicted_class)
        disease = "Unknown Disease" if "low_confidence" in notes else predicted_class
        logger.info(
            "Prediction complete crop=%s predicted_index=%s disease=%s confidence=%.2f duration_ms=%.2f",
            model_type,
            predicted_index,
            predicted_class,
            confidence,
            (time.perf_counter() - started_at) * 1000,
        )
        memory_snapshot("after_prediction", crop=model_type)

        return {
            "crop": model_type,
            "disease": disease,
            "class_name": predicted_class,
            "confidence": round(confidence, 2),
            "top_predictions": top_predictions,
            "recommendations": recommendations,
            "recommendation": recommendations,
            "image_quality_score": quality,
            "low_confidence": "low_confidence" in notes,
            "warning": "Low confidence prediction. Please upload a clearer crop image." if "low_confidence" in notes else "",
            "notes": notes,
            "all_scores": {
                class_names[index]: round(float(scores[index] * 100), 2)
                for index in range(len(class_names))
            },
            "model_file": model_file,
        }
    except ValueError as exc:
        logger.warning("Prediction invalid input crop=%s image_path=%s error=%s", model_type, image_path, exc)
        return {
            "error": "Invalid image",
            "exception_type": type(exc).__name__,
            "message": str(exc),
        }
    except Exception as exc:
        logger.exception("Prediction exception crop=%s image_path=%s", model_type, image_path)
        return {
            "error": "Prediction failed",
            "exception_type": type(exc).__name__,
            "message": str(exc),
        }
    finally:
        unload_idle_models(except_crop=model_type)
        evict_model_cache(except_crop=model_type)
        if UNLOAD_MODEL_AFTER_PREDICTION:
            unload_model(model_type, reason="after_prediction")
        gc.collect()
        memory_snapshot("after_prediction_gc", crop=model_type)


def find_last_conv_layer(model) -> None:
    return None


def create_gradcam(image_path, model_type, output_path=None):
    logger.warning(
        "Grad-CAM requested but unavailable for TFLite-only runtime crop=%s image_path=%s",
        model_type,
        image_path,
    )
    return {
        "error": "Grad-CAM unavailable for TensorFlow Lite runtime",
        "crop": model_type,
        "message": "TFLite interpreters do not expose Keras layers or gradients required for Grad-CAM.",
    }
