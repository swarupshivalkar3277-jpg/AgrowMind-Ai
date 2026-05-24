from __future__ import annotations

import json
from pathlib import Path

import tensorflow as tf


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DATASETS_DIR = PROJECT_DIR / "datasets"
TRAINING_DIR = BASE_DIR / "training"
CLASS_NAMES_DIR = TRAINING_DIR / "class_names"
CROPS = ("tomato", "mango", "coconut")


def dataset_classes(crop: str) -> list[str]:
    dataset_dir = DATASETS_DIR / crop
    return sorted(path.name for path in dataset_dir.iterdir() if path.is_dir())


def load_json_list(path: Path) -> list[str]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def model_output_size(crop: str) -> int | None:
    model_path = TRAINING_DIR / f"{crop}_model.keras"
    if not model_path.exists():
        return None
    model = tf.keras.models.load_model(model_path, compile=False)
    return int(model.output_shape[-1])


def main() -> None:
    report = []
    for crop in CROPS:
        classes = dataset_classes(crop)
        metadata_classes = load_json_list(CLASS_NAMES_DIR / f"{crop}_classes.json")
        output_size = model_output_size(crop)
        mismatches = []

        if len(classes) != len(metadata_classes):
            mismatches.append("dataset_class_count != metadata_class_count")
        if output_size is None:
            mismatches.append("model_missing")
        elif output_size != len(metadata_classes):
            mismatches.append("model_output_size != metadata_class_count")
        if classes != metadata_classes:
            mismatches.append("dataset_class_order != metadata_class_order")

        report.append({
            "crop": crop,
            "dataset_class_count": len(classes),
            "saved_model_output_size": output_size,
            "metadata_class_count": len(metadata_classes),
            "mismatches": mismatches,
            "classes": metadata_classes,
        })

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
