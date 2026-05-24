from __future__ import annotations

import json
import sys
from pathlib import Path

import tensorflow as tf

from ai.recommendations import validate_recommendation_coverage


BASE_DIR = Path(__file__).resolve().parent
TRAINING_DIR = BASE_DIR / "training"
CLASS_NAMES_DIR = TRAINING_DIR / "class_names"
CROPS = ("tomato", "mango", "coconut")


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def class_names_from_payload(payload) -> list[str]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("class_names", [])
    return []


def audit_crop(crop: str) -> dict:
    failures = []
    model_path = TRAINING_DIR / f"{crop}_model.keras"
    metadata_path = TRAINING_DIR / f"{crop}_model.json"
    class_path = CLASS_NAMES_DIR / f"{crop}_classes.json"

    metadata = {}
    class_names = []
    output_neurons = None

    try:
        metadata = load_json(metadata_path)
    except Exception as exc:
        failures.append(str(exc))

    try:
        class_names = class_names_from_payload(load_json(class_path))
        if not class_names:
            failures.append(f"No class names found in {class_path}")
    except Exception as exc:
        failures.append(str(exc))

    try:
        if not model_path.exists():
            raise FileNotFoundError(f"Missing file: {model_path}")
        model = tf.keras.models.load_model(model_path, compile=False)
        output_neurons = int(model.output_shape[-1])
    except Exception as exc:
        failures.append(str(exc))

    metadata_classes = metadata.get("class_names", []) if isinstance(metadata, dict) else []
    if metadata_classes and class_names and metadata_classes != class_names:
        failures.append("metadata class_names differ from class JSON")

    if output_neurons is not None and class_names and output_neurons != len(class_names):
        failures.append(f"model output neurons {output_neurons} != class count {len(class_names)}")

    if metadata.get("class_count") and metadata.get("class_count") != len(class_names):
        failures.append(f"metadata class_count {metadata.get('class_count')} != class JSON count {len(class_names)}")

    evaluation = metadata.get("evaluation", {}) if isinstance(metadata, dict) else {}
    per_class = evaluation.get("per_class", {}) if isinstance(evaluation, dict) else {}
    zero_support = [name for name in class_names if int(per_class.get(name, {}).get("support", 0)) <= 0]
    if zero_support:
        failures.append(f"evaluation support missing/zero for classes: {zero_support}")

    missing_recommendations = validate_recommendation_coverage(crop, class_names) if class_names else []
    if missing_recommendations:
        failures.append(f"recommendation mappings missing for classes: {missing_recommendations}")

    return {
        "crop": crop,
        "model_path": str(model_path),
        "metadata_path": str(metadata_path),
        "class_names_path": str(class_path),
        "detected_classes": class_names,
        "class_count": len(class_names),
        "output_neurons": output_neurons,
        "validation_accuracy": metadata.get("validation_accuracy"),
        "recommendation_coverage": len(missing_recommendations) == 0,
        "deployment_ready": not failures,
        "failures": failures,
    }


def main() -> int:
    report = [audit_crop(crop) for crop in CROPS]
    print(json.dumps({"success": all(item["deployment_ready"] for item in report), "crops": report}, indent=2))
    return 0 if all(item["deployment_ready"] for item in report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
