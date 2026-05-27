from __future__ import annotations

import json
import logging
import os
import gc
import shutil
import threading
import time
import urllib.error
import urllib.request
import zipfile
from collections import OrderedDict
from pathlib import Path

import numpy as np
import psutil
from PIL import Image

from ai.recommendations import recommendation_for, validate_recommendation_coverage


tf = None
logger = logging.getLogger("agromind.ai.predict")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BASE_DIR.parent
AI_DIR = Path(__file__).resolve().parent
TRAINING_DIR = BASE_DIR / "training"
CLASS_NAMES_DIR = TRAINING_DIR / "class_names"
MODEL_DIRS = [
    Path(path).expanduser()
    for path in os.getenv("MODEL_DIRS", "").split(os.pathsep)
    if path.strip()
] or [
    TRAINING_DIR,
    AI_DIR / "models",
    BASE_DIR / "models",
    PROJECT_DIR,
]
IMG_SIZE = 224
SUPPORTED_CROPS = ("tomato", "mango", "coconut")

loaded_models = OrderedDict()
model_locks = {crop: threading.Lock() for crop in SUPPORTED_CROPS}
MIN_MODEL_BYTES = 1024
MAX_LOADED_MODELS = max(1, int(os.getenv("MAX_LOADED_MODELS", "1")))


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


def get_tensorflow():
    global tf

    if tf is None:
        import tensorflow as tensorflow_module

        tf = tensorflow_module
        try:
            tf.config.set_visible_devices([], "GPU")
        except Exception:
            logger.debug("TensorFlow GPU visibility could not be changed after import", exc_info=True)
        try:
            tf.config.threading.set_inter_op_parallelism_threads(int(os.getenv("TF_INTER_OP_THREADS", "1")))
            tf.config.threading.set_intra_op_parallelism_threads(int(os.getenv("TF_INTRA_OP_THREADS", "1")))
        except Exception:
            logger.debug("TensorFlow thread limits could not be set", exc_info=True)
        memory_snapshot("tensorflow_imported")

    return tf


def evict_model_cache(except_crop: str | None = None) -> None:
    while len(loaded_models) > MAX_LOADED_MODELS:
        evict_crop = next((crop for crop in loaded_models if crop != except_crop), None)
        if evict_crop is None:
            return
        loaded_models.pop(evict_crop, None)
        logger.info("Evicted TensorFlow model from cache crop=%s max_loaded_models=%s", evict_crop, MAX_LOADED_MODELS)
        gc.collect()
        memory_snapshot("model_evicted", crop=evict_crop)


def model_path_for_crop(crop: str) -> Path:
    candidates = candidate_model_paths(crop)
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def candidate_model_paths(crop: str) -> list[Path]:
    filenames = (
        f"{crop}_model.keras",
        f"{crop}_model.h5",
        f"{crop}.keras",
        f"{crop}.h5",
    )

    return [
        model_dir / filename
        for model_dir in MODEL_DIRS
        for filename in filenames
    ]


def configured_model_url(crop: str) -> str | None:
    crop_key = crop.upper()
    direct_url = os.getenv(f"{crop_key}_MODEL_URL")

    if direct_url:
        return direct_url.strip()

    base_url = os.getenv("MODEL_BASE_URL", "").strip().rstrip("/")
    if base_url:
        return f"{base_url}/{crop}_model.keras"

    return None


def expected_class_count(crop: str) -> int | None:
    try:
        return len(load_class_names(crop))
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return None


def keras_output_size_from_config(model_path: Path) -> int | None:
    if model_path.suffix.lower() != ".keras":
        return None

    try:
        with zipfile.ZipFile(model_path) as archive:
            config = json.loads(archive.read("config.json"))
    except (KeyError, OSError, json.JSONDecodeError, zipfile.BadZipFile):
        return None

    layers_config = config.get("config", {}).get("layers", [])
    dense_layers = [
        layer
        for layer in layers_config
        if layer.get("class_name") == "Dense" and layer.get("config", {}).get("units")
    ]
    if not dense_layers:
        return None
    return int(dense_layers[-1]["config"]["units"])


def output_shape_from_artifact(model_path: Path) -> str | None:
    output_size = keras_output_size_from_config(model_path)
    if output_size is None:
        return None
    return f"(None, {output_size})"


def validate_downloaded_model_artifact(crop: str, model_path: Path) -> None:
    expected_count = expected_class_count(crop)
    output_size = keras_output_size_from_config(model_path)
    logger.info(
        "Model artifact validation crop=%s download_url=%s downloaded_file_size=%s model_output_shape=%s class_count=%s",
        crop,
        configured_model_url(crop),
        model_path.stat().st_size if model_path.exists() else None,
        output_shape_from_artifact(model_path),
        expected_count,
    )
    if expected_count is None or output_size is None:
        return
    if expected_count != output_size:
        raise RuntimeError(
            f"Downloaded {crop} model output size {output_size} does not match "
            f"class metadata count {expected_count}. Check {crop.upper()}_MODEL_URL."
        )


def model_artifact_error(crop: str, model_path: Path) -> dict | None:
    size_bytes = model_path.stat().st_size
    if size_bytes < MIN_MODEL_BYTES:
        return {
            "error": f"{crop} model artifact is invalid",
            "crop": crop,
            "path": str(model_path),
            "size_bytes": size_bytes,
            "message": "Model file is too small to be a valid trained model.",
        }

    expected_count = expected_class_count(crop)
    output_size = keras_output_size_from_config(model_path)
    if expected_count is not None and output_size is not None and expected_count != output_size:
        return {
            "error": "Model output size does not match class metadata",
            "crop": crop,
            "class_count": expected_count,
            "output_size": output_size,
            "model_output_shape": output_shape_from_artifact(model_path),
            "class_names_path": str(class_names_path(crop)),
            "model_path": str(model_path),
            "message": (
                f"{crop} model has {output_size} outputs but class metadata has "
                f"{expected_count} classes. Update {crop.upper()}_MODEL_URL to the correct model "
                "or retrain with the expected dataset classes."
            ),
        }

    return None


def download_model_if_configured(crop: str) -> Path | None:
    url = configured_model_url(crop)
    if not url:
        return None

    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    destination = TRAINING_DIR / f"{crop}_model.keras"
    temp_path = destination.with_suffix(".download")

    try:
        logger.info("Downloading model crop=%s download_url=%s", crop, url)
        with urllib.request.urlopen(url, timeout=180) as response:
            with temp_path.open("wb") as output:
                shutil.copyfileobj(response, output)

        logger.info(
            "Downloaded model artifact crop=%s download_url=%s downloaded_file_size=%s",
            crop,
            url,
            temp_path.stat().st_size if temp_path.exists() else None,
        )
        if temp_path.stat().st_size < MIN_MODEL_BYTES:
            temp_path.unlink(missing_ok=True)
            raise RuntimeError(f"Downloaded {crop} model is too small to be valid")

        validate_downloaded_model_artifact(crop, temp_path)
        temp_path.replace(destination)
        logger.info("Downloaded %s model to %s size_bytes=%s", crop, destination, destination.stat().st_size)
        return destination
    except (urllib.error.URLError, OSError, RuntimeError) as exc:
        temp_path.unlink(missing_ok=True)
        logger.exception("Model download failed crop=%s url=%s", crop, url)
        raise RuntimeError(f"Could not download {crop} model from {url}: {exc}") from exc


def ensure_configured_models() -> dict[str, str]:
    results = {}

    for crop in SUPPORTED_CROPS:
        try:
            if not any(path.exists() for path in candidate_model_paths(crop)) and configured_model_url(crop):
                download_model_if_configured(crop)

            model_path = next((path for path in candidate_model_paths(crop) if path.exists()), None)
            if not model_path:
                results[crop] = "missing"
                logger.warning(
                    "Model startup warning crop=%s download_url=%s reason=model_not_found",
                    crop,
                    configured_model_url(crop),
                )
                continue

            size_bytes = model_path.stat().st_size
            expected_count = expected_class_count(crop)
            output_size = keras_output_size_from_config(model_path)
            output_shape = output_shape_from_artifact(model_path)
            logger.info(
                "Model startup artifact check crop=%s download_url=%s path=%s downloaded_file_size=%s model_output_shape=%s class_count=%s",
                crop,
                configured_model_url(crop),
                model_path,
                size_bytes,
                output_shape,
                expected_count,
            )
            if size_bytes < MIN_MODEL_BYTES:
                results[crop] = "invalid:file_too_small"
                logger.warning("Model startup warning crop=%s reason=file_too_small size_bytes=%s", crop, size_bytes)
                continue
            if expected_count is not None and output_size is not None and expected_count != output_size:
                results[crop] = "invalid:output_shape_mismatch"
                logger.warning(
                    "Model startup warning crop=%s reason=output_shape_mismatch output_size=%s class_count=%s",
                    crop,
                    output_size,
                    expected_count,
                )
                continue

            results[crop] = f"available:{model_path}"
        except Exception as exc:
            results[crop] = f"exception:{type(exc).__name__}"
            logger.exception("Model startup exception crop=%s", crop)
        if crop not in results:
            results[crop] = "missing"

    return results


def model_loaded_status() -> dict[str, str]:
    return {
        crop: "loaded" if crop in loaded_models else "not_loaded"
        for crop in SUPPORTED_CROPS
    }


def model_status() -> dict:
    status = {}

    for crop in SUPPORTED_CROPS:
        candidates = candidate_model_paths(crop)
        available_path = next((path for path in candidates if path.exists()), None)
        size_bytes = available_path.stat().st_size if available_path else None
        warnings = []

        if available_path and size_bytes is not None and size_bytes < MIN_MODEL_BYTES:
            warnings.append(
                "model_file_is_too_small_to_be_a_valid_trained_model"
            )

        class_metadata = []
        try:
            class_metadata = load_class_names(crop)
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            warnings.append(f"class_metadata_unavailable:{exc}")

        model_output_size = keras_output_size_from_config(available_path) if available_path else None
        if class_metadata and model_output_size is not None and len(class_metadata) != model_output_size:
            warnings.append("model_output_size_does_not_match_class_metadata")

        status[crop] = {
            "available": available_path is not None and not warnings,
            "loaded": crop in loaded_models,
            "path": str(available_path) if available_path else None,
            "size_bytes": size_bytes,
            "download_url": configured_model_url(crop),
            "model_output_shape": output_shape_from_artifact(available_path) if available_path else None,
            "class_names_path": str(class_names_path(crop)),
            "metadata_class_count": len(class_metadata),
            "warnings": warnings,
            "candidates": [str(path) for path in candidates],
        }

    return status


def metadata_path_for_model(model_path: Path) -> Path:
    return model_path.with_suffix(".json")


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
    metadata_path = metadata_path_for_model(model_path)
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
    logger.info("Resolving model crop=%s selected_path=%s", crop, model_path)
    if not model_path.exists():
        download_model_if_configured(crop)
        model_path = model_path_for_crop(crop)

    if not model_path.exists():
        return None, None, {
            "error": f"{crop} model not found",
            "path": str(model_path),
            "candidates": [str(path) for path in candidate_model_paths(crop)],
            "hint": (
                f"Add {crop}_model.keras to backend/training, commit it, "
                f"or set {crop.upper()}_MODEL_URL / MODEL_BASE_URL on the deployed backend."
            ),
        }

    modified_at = model_path.stat().st_mtime
    class_metadata_path = class_names_path(crop)
    class_metadata_modified_at = class_metadata_path.stat().st_mtime if class_metadata_path.exists() else None
    cache_entry = loaded_models.get(crop)
    artifact_error = model_artifact_error(crop, model_path)
    if artifact_error:
        logger.error("Model artifact validation failed crop=%s error=%s", crop, artifact_error)
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
                return entry["model"], entry["metadata"], None

            return _load_crop_model_uncached(crop, model_path, modified_at, class_metadata_modified_at)
    else:
        logger.debug("Using cached model crop=%s path=%s", crop, model_path)

    loaded_models.move_to_end(crop)
    entry = loaded_models[crop]
    return entry["model"], entry["metadata"], None


def _load_crop_model_uncached(crop: str, model_path: Path, modified_at: float, class_metadata_modified_at: float | None):
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
        memory_snapshot("before_model_load", crop=crop, path=str(model_path))
        logger.info("Loading TensorFlow model crop=%s path=%s size_bytes=%s", crop, model_path, model_path.stat().st_size)
        model = get_tensorflow().keras.models.load_model(model_path, compile=False)
    except Exception as exc:
        logger.exception("TensorFlow model load failed crop=%s path=%s", crop, model_path)
        return None, None, {
            "error": f"{crop} model could not be loaded",
            "path": str(model_path),
            "message": str(exc),
            "hint": (
                "Restore a valid trained .keras/.h5 model file at this path "
                "or set MODEL_DIRS to a directory that contains it."
            ),
        }

    output_size = int(model.output_shape[-1])
    if len(class_names) != output_size:
        return None, None, {
            "error": "Model output size does not match class metadata",
            "crop": crop,
            "class_count": len(class_names),
            "output_size": output_size,
            "model_output_shape": str(getattr(model, "output_shape", None)),
            "class_names_path": str(class_names_path(crop)),
            "model_path": str(model_path),
        }

    missing_recommendations = validate_recommendation_coverage(crop, class_names)
    if missing_recommendations:
        return None, None, {
            "error": "Recommendation mappings missing",
            "crop": crop,
            "missing_recommendations": missing_recommendations,
        }

    metadata["class_names"] = class_names
    loaded_models[crop] = {
        "path": model_path,
        "modified_at": modified_at,
        "class_metadata_modified_at": class_metadata_modified_at,
        "model": model,
        "metadata": metadata,
    }
    loaded_models.move_to_end(crop)
    evict_model_cache(except_crop=crop)
    logger.info(
        "TensorFlow model cached crop=%s path=%s input_shape=%s output_shape=%s",
        crop,
        model_path,
        getattr(model, "input_shape", None),
        getattr(model, "output_shape", None),
    )
    memory_snapshot("after_model_load", crop=crop, path=str(model_path))

    entry = loaded_models[crop]
    return entry["model"], entry["metadata"], None


def get_model_image_size(model, metadata: dict) -> tuple[int, int]:
    metadata_size = metadata.get("image_size")
    if isinstance(metadata_size, list) and len(metadata_size) == 2:
        return int(metadata_size[0]), int(metadata_size[1])

    input_shape = model.input_shape[0] if isinstance(model.input_shape, list) else model.input_shape
    height = input_shape[1] or IMG_SIZE
    width = input_shape[2] or IMG_SIZE
    return int(width), int(height)


def image_to_batch(image_path: str | Path, size: tuple[int, int]) -> np.ndarray:
    logger.info("Preprocessing image path=%s target_size=%s", image_path, size)
    image = Image.open(image_path).convert("RGB")
    image = image.resize(size, Image.Resampling.BILINEAR)
    array = np.asarray(image, dtype=np.float32)
    return np.expand_dims(array, axis=0)


def image_quality_score(batch: np.ndarray) -> float:
    image = np.squeeze(batch).astype(np.float32)
    contrast = float(np.std(image) / 64.0)
    brightness = float(1.0 - abs(np.mean(image) - 127.5) / 127.5)
    return round(max(0.0, min(1.0, (contrast * 0.55) + (brightness * 0.45))) * 100, 2)


def apply_input_scale(batch: np.ndarray, metadata: dict) -> np.ndarray:
    input_scale = str(metadata.get("input_scale", "model_includes_preprocessing")).lower()
    if input_scale in {"rescale_0_1", "0_1"}:
        logger.debug("Applying 0..1 input scaling")
        return batch / 255.0
    if input_scale in {"mobilenetv2_-1_1", "rescale_-1_1", "-1_1"}:
        logger.debug("Applying MobileNetV2 -1..1 input scaling")
        return (batch / 127.5) - 1.0
    logger.debug("Leaving image batch unscaled because model metadata input_scale=%s", input_scale)
    return batch


def normalize_scores(raw_scores: np.ndarray, temperature: float) -> np.ndarray:
    scores = np.asarray(raw_scores, dtype=np.float64)
    scores = np.squeeze(scores)
    tensorflow = get_tensorflow()

    if not np.isclose(np.sum(scores), 1.0, atol=1e-3):
        scores = tensorflow.nn.softmax(scores / max(temperature, 1e-6)).numpy()
    elif temperature and temperature != 1.0:
        scores = np.log(np.clip(scores, 1e-8, 1.0)) / temperature
        scores = tensorflow.nn.softmax(scores).numpy()

    return scores.astype(np.float32)


def class_names_for_scores(crop: str, metadata: dict, scores: np.ndarray, model) -> list[str]:
    metadata_classes = metadata.get("class_names") or []
    output_size = len(scores)

    if len(metadata_classes) == output_size:
        return metadata_classes

    raise ValueError(
        "Model output size does not match class metadata: "
        f"crop={crop}, class_count={len(metadata_classes)}, output_size={output_size}, "
        f"model_output_shape={getattr(model, 'output_shape', None)}"
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
    try:
        logger.info("Prediction started crop=%s image_path=%s", model_type, image_path)
        memory_snapshot("before_prediction", crop=model_type)
        model, metadata, error = load_crop_model(model_type)
        if error:
            logger.error("Prediction cannot load model crop=%s error=%s", model_type, error)
            return error

        image_size = get_model_image_size(model, metadata)
        raw_batch = image_to_batch(image_path, image_size)
        quality = image_quality_score(raw_batch)
        batch = apply_input_scale(raw_batch, metadata)

        logger.info(
            "Running prediction crop=%s image_size=%s class_count=%s model_output_shape=%s",
            model_type,
            image_size,
            len(metadata.get("class_names") or []),
            getattr(model, "output_shape", None),
        )
        raw_prediction = model.predict(batch, verbose=0)[0]
        scores = normalize_scores(raw_prediction, float(metadata.get("temperature", 1.0)))
        try:
            class_names = class_names_for_scores(model_type, metadata, scores, model)
        except ValueError as exc:
            error = {
                "error": "Model output size does not match class metadata",
                "crop": model_type,
                "class_count": int(len(metadata.get("class_names") or [])),
                "output_size": int(len(scores)),
                "model_output_shape": str(getattr(model, "output_shape", None)),
                "class_names_path": str(class_names_path(model_type)),
                "message": str(exc),
            }
            logger.error("Class validation failed crop=%s error=%s", model_type, error)
            return error

        predicted_index = int(np.argmax(scores))
        predicted_class = class_names[predicted_index]
        confidence = float(scores[predicted_index] * 100)
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
            "model_file": str(loaded_models[model_type]["path"]),
        }
    except Exception as exc:
        logger.exception("Prediction exception crop=%s image_path=%s", model_type, image_path)
        return {
            "error": "Prediction failed",
            "exception_type": type(exc).__name__,
            "message": str(exc),
        }


def find_last_conv_layer(model: tf.keras.Model) -> str | None:
    tensorflow = get_tensorflow()

    for layer in reversed(model.layers):
        if isinstance(layer, tensorflow.keras.layers.Conv2D):
            return layer.name
    return None


def create_gradcam(image_path, model_type, output_path=None):
    try:
        logger.info("Grad-CAM started crop=%s image_path=%s", model_type, image_path)
        model, metadata, error = load_crop_model(model_type)
        if error:
            logger.error("Grad-CAM cannot load model crop=%s error=%s", model_type, error)
            return error

        image_size = get_model_image_size(model, metadata)
        batch = apply_input_scale(image_to_batch(image_path, image_size), metadata)
        last_conv_layer_name = find_last_conv_layer(model)
        tensorflow = get_tensorflow()

        if last_conv_layer_name is None:
            logger.error("Grad-CAM failed crop=%s reason=no_conv2d_layer", model_type)
            return {"error": "No Conv2D layer found for Grad-CAM"}

        grad_model = tensorflow.keras.Model(
            model.inputs,
            [model.get_layer(last_conv_layer_name).output, model.output],
        )

        with tensorflow.GradientTape() as tape:
            conv_outputs, predictions = grad_model(batch)
            predicted_index = tensorflow.argmax(predictions[0])
            class_score = predictions[:, predicted_index]

        grads = tape.gradient(class_score, conv_outputs)
        pooled_grads = tensorflow.reduce_mean(grads, axis=(0, 1, 2))
        heatmap = tensorflow.reduce_sum(conv_outputs[0] * pooled_grads, axis=-1)
        heatmap = tensorflow.maximum(heatmap, 0) / tensorflow.maximum(tensorflow.reduce_max(heatmap), 1e-8)
        heatmap = heatmap.numpy()

        original = Image.open(image_path).convert("RGB").resize(image_size, Image.Resampling.BILINEAR)
        heatmap_image = Image.fromarray(np.uint8(255 * heatmap)).resize(image_size, Image.Resampling.BILINEAR)
        heatmap_image = heatmap_image.convert("L")

        red_overlay = Image.new("RGBA", image_size, (255, 0, 0, 0))
        red_overlay.putalpha(heatmap_image.point(lambda value: int(value * 0.45)))
        cam = Image.alpha_composite(original.convert("RGBA"), red_overlay).convert("RGB")

        if output_path is None:
            output_dir = BASE_DIR / "results"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"gradcam_{Path(image_path).stem}.jpg"

        cam.save(output_path)
        logger.info("Grad-CAM complete crop=%s layer=%s output_path=%s", model_type, last_conv_layer_name, output_path)
        return {"gradcam_image": str(output_path), "layer": last_conv_layer_name}
    except Exception as exc:
        logger.exception("Grad-CAM exception crop=%s image_path=%s", model_type, image_path)
        return {
            "error": "Grad-CAM failed",
            "exception_type": type(exc).__name__,
            "message": str(exc),
        }
