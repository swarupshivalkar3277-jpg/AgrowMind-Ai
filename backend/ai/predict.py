from __future__ import annotations

import json
import os
import shutil
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image


tf = None
BASE_DIR = Path(__file__).resolve().parents[1]
AI_DIR = Path(__file__).resolve().parent
TRAINING_DIR = BASE_DIR / "training"
MODEL_DIRS = [
    Path(path).expanduser()
    for path in os.getenv("MODEL_DIRS", "").split(os.pathsep)
    if path.strip()
] or [
    TRAINING_DIR,
    AI_DIR / "models",
    BASE_DIR / "models",
]
IMG_SIZE = 224

DEFAULT_CLASSES = {
    "tomato": ["early_blight", "healthy", "late_blight"],
    "mango": ["anthracnose", "healthy", "powdery_mildew"],
    "coconut": ["bud_rot", "healthy", "leaf_rot"],
}

loaded_models = {}
MIN_MODEL_BYTES = 1024


def get_tensorflow():
    global tf

    if tf is None:
        import tensorflow as tensorflow_module

        tf = tensorflow_module

    return tf


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


def download_model_if_configured(crop: str) -> Path | None:
    url = configured_model_url(crop)
    if not url:
        return None

    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    destination = TRAINING_DIR / f"{crop}_model.keras"
    temp_path = destination.with_suffix(".download")

    try:
        with urllib.request.urlopen(url, timeout=180) as response:
            with temp_path.open("wb") as output:
                shutil.copyfileobj(response, output)

        if temp_path.stat().st_size < MIN_MODEL_BYTES:
            temp_path.unlink(missing_ok=True)
            raise RuntimeError(f"Downloaded {crop} model is too small to be valid")

        temp_path.replace(destination)
        return destination
    except (urllib.error.URLError, OSError, RuntimeError) as exc:
        temp_path.unlink(missing_ok=True)
        raise RuntimeError(f"Could not download {crop} model from {url}: {exc}") from exc


def ensure_configured_models() -> dict[str, str]:
    results = {}

    for crop in DEFAULT_CLASSES:
        if any(path.exists() for path in candidate_model_paths(crop)):
            results[crop] = "available"
            continue

        if configured_model_url(crop):
            downloaded_path = download_model_if_configured(crop)
            results[crop] = f"downloaded:{downloaded_path}" if downloaded_path else "missing"
        else:
            results[crop] = "missing"

    return results


def model_status() -> dict:
    status = {}

    for crop in DEFAULT_CLASSES:
        candidates = candidate_model_paths(crop)
        available_path = next((path for path in candidates if path.exists()), None)
        size_bytes = available_path.stat().st_size if available_path else None
        warnings = []

        if available_path and size_bytes is not None and size_bytes < MIN_MODEL_BYTES:
            warnings.append(
                "model_file_is_too_small_to_be_a_valid_trained_model"
            )

        status[crop] = {
            "available": available_path is not None and not warnings,
            "path": str(available_path) if available_path else None,
            "size_bytes": size_bytes,
            "warnings": warnings,
            "candidates": [str(path) for path in candidates],
        }

    return status


def metadata_path_for_model(model_path: Path) -> Path:
    return model_path.with_suffix(".json")


def load_metadata(crop: str, model_path: Path) -> dict:
    metadata_path = metadata_path_for_model(model_path)
    if metadata_path.exists():
        with metadata_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    return {
        "crop": crop,
        "class_names": DEFAULT_CLASSES.get(crop, []),
        "image_size": [IMG_SIZE, IMG_SIZE],
        "temperature": 1.0,
        "input_scale": "model_includes_preprocessing",
    }


def load_crop_model(crop: str):
    if crop not in DEFAULT_CLASSES:
        return None, None, {"error": "Invalid crop type"}

    model_path = model_path_for_crop(crop)
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
    cache_entry = loaded_models.get(crop)

    if cache_entry is None or cache_entry["path"] != model_path or cache_entry["modified_at"] != modified_at:
        metadata = load_metadata(crop, model_path)
        try:
            model = get_tensorflow().keras.models.load_model(model_path, compile=False)
        except Exception as exc:
            return None, None, {
                "error": f"{crop} model could not be loaded",
                "path": str(model_path),
                "message": str(exc),
                "hint": (
                    "Restore a valid trained .keras/.h5 model file at this path "
                    "or set MODEL_DIRS to a directory that contains it."
                ),
            }

        loaded_models[crop] = {
            "path": model_path,
            "modified_at": modified_at,
            "model": model,
            "metadata": metadata,
        }

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
    image = Image.open(image_path).convert("RGB")
    image = image.resize(size, Image.Resampling.BILINEAR)
    array = np.asarray(image, dtype=np.float32)
    return np.expand_dims(array, axis=0)


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


def confidence_notes(scores: np.ndarray) -> list[str]:
    sorted_scores = np.sort(scores)[::-1]
    top_score = float(sorted_scores[0])
    margin = float(sorted_scores[0] - sorted_scores[1]) if len(sorted_scores) > 1 else top_score

    notes = []
    if top_score < 0.60:
        notes.append("low_confidence")
    if margin < 0.15:
        notes.append("ambiguous_top_classes")
    return notes


def predict_image(image_path, model_type):
    model, metadata, error = load_crop_model(model_type)
    if error:
        return error

    class_names = metadata.get("class_names") or DEFAULT_CLASSES[model_type]
    image_size = get_model_image_size(model, metadata)
    batch = image_to_batch(image_path, image_size)

    raw_prediction = model.predict(batch, verbose=0)[0]
    scores = normalize_scores(raw_prediction, float(metadata.get("temperature", 1.0)))

    if len(class_names) != len(scores):
        return {
            "error": "Model output size does not match class metadata",
            "classes": class_names,
            "output_size": int(len(scores)),
        }

    predicted_index = int(np.argmax(scores))
    predicted_class = class_names[predicted_index]
    confidence = float(scores[predicted_index] * 100)

    return {
        "disease": predicted_class,
        "confidence": round(confidence, 2),
        "notes": confidence_notes(scores),
        "all_scores": {
            class_names[index]: round(float(scores[index] * 100), 2)
            for index in range(len(class_names))
        },
        "model_file": str(loaded_models[model_type]["path"]),
    }


def find_last_conv_layer(model: tf.keras.Model) -> str | None:
    tensorflow = get_tensorflow()

    for layer in reversed(model.layers):
        if isinstance(layer, tensorflow.keras.layers.Conv2D):
            return layer.name
    return None


def create_gradcam(image_path, model_type, output_path=None):
    model, metadata, error = load_crop_model(model_type)
    if error:
        return error

    image_size = get_model_image_size(model, metadata)
    batch = image_to_batch(image_path, image_size)
    last_conv_layer_name = find_last_conv_layer(model)
    tensorflow = get_tensorflow()

    if last_conv_layer_name is None:
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
    return {"gradcam_image": str(output_path), "layer": last_conv_layer_name}
