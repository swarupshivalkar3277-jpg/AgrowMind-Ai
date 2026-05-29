from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai.predict import (
    SUPPORTED_CROPS,
    _quantization_text,
    _shape_from_detail,
    apply_input_scale,
    class_names_for_scores,
    get_model_image_size,
    image_to_batch,
    load_crop_model,
    normalize_scores,
    predict_tflite,
)


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def first_dataset_image() -> Path:
    datasets_dir = PROJECT_DIR / "datasets"
    for crop in SUPPORTED_CROPS:
        crop_dir = datasets_dir / crop
        if not crop_dir.exists():
            continue
        for path in crop_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                return path
    raise FileNotFoundError(f"No sample image found under {datasets_dir}")


def validate_image(image_path: Path) -> dict:
    rows = []
    for crop in SUPPORTED_CROPS:
        interpreter, metadata, error = load_crop_model(crop)
        if error:
            rows.append({"crop": crop, "error": error})
            continue

        image_size = get_model_image_size(interpreter, metadata)
        raw_batch = image_to_batch(image_path, image_size)
        batch, preprocessing = apply_input_scale(raw_batch, crop, metadata)
        prediction = predict_tflite(interpreter, batch)
        scores = normalize_scores(np.squeeze(prediction), float(metadata.get("temperature", 1.0)))
        class_names = class_names_for_scores(crop, metadata, scores, interpreter)
        predicted_index = int(np.argmax(scores))
        input_detail = interpreter.get_input_details()[0]

        rows.append({
            "crop": crop,
            "model_file": metadata.get("model_file"),
            "preprocessing_method": preprocessing["method"],
            "preprocessing_mode": preprocessing["mode"],
            "tensor_dtype": str(batch.dtype),
            "tensor_shape": tuple(int(dim) for dim in batch.shape),
            "tensor_min": round(float(np.min(batch)), 6),
            "tensor_max": round(float(np.max(batch)), 6),
            "input_dtype": str(input_detail.get("dtype")),
            "input_shape": _shape_from_detail(input_detail),
            "input_quantization": _quantization_text(input_detail),
            "top_prediction": class_names[predicted_index],
            "confidence": round(float(scores[predicted_index] * 100), 2),
        })
    return {"image": str(image_path), "results": rows}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate TFLite preprocessing for all crop models.")
    parser.add_argument(
        "--image",
        type=Path,
        default=None,
        help="Image to run through tomato, mango, and coconut models. Defaults to the first dataset image.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    image_path = args.image or first_dataset_image()
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    print(json.dumps(validate_image(image_path), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
