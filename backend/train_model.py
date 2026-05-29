import argparse
import csv
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DATASETS_DIR = PROJECT_DIR / "datasets"
TRAINING_DIR = BASE_DIR / "training"
CLASS_NAMES_DIR = TRAINING_DIR / "class_names"

IMG_SIZE = 224
BATCH_SIZE = 32
SEED = 123
INITIAL_EPOCHS = 20
FINE_TUNE_EPOCHS = 10
SUPPORTED_CROPS = ("tomato", "mango", "coconut")
EXPECTED_CLASS_COUNTS = {
    "tomato": 10,
    "mango": 8,
    "coconut": 6,
}
EXPECTED_CLASSES = {
    "tomato": [
    "bacterial_spot",
    "early_blight",
    "healthy",
    "late_blight",
    "leaf_mold",
    "mosaic_virus",
    "septoria_leaf_spot",
    "target_spot",
    "twospotted_spider_mite",
    "yellow_leaf_curl_virus",
],
}


def set_reproducibility(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)


def count_images(dataset_dir: Path) -> dict[str, int]:
    counts = {}
    for class_dir in sorted(path for path in dataset_dir.iterdir() if path.is_dir()):
        counts[class_dir.name] = sum(1 for path in class_dir.rglob("*") if path.is_file())
    return counts


def save_dataset_audit(crop: str, counts: dict[str, int], min_images: int) -> Path:
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    audit_path = TRAINING_DIR / f"{crop}_dataset_audit.json"
    payload = {
        "crop": crop,
        "discovered_classes": sorted(counts),
        "class_count": len(counts),
        "image_counts": counts,
        "total_images": sum(counts.values()),
        "min_images_per_class": min_images,
    }
    audit_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return audit_path


def validate_dataset(crop: str, dataset_dir: Path, min_images: int) -> dict[str, int]:
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset folder not found: {dataset_dir}")

    counts = count_images(dataset_dir)
    audit_path = save_dataset_audit(crop, counts, min_images)
    print(f"Discovered classes for {crop}: {sorted(counts)}")
    print(f"Image counts for {crop}: {counts}")
    print(f"Total images for {crop}: {sum(counts.values())}")
    print(f"Dataset audit saved: {audit_path}")

    expected = EXPECTED_CLASSES.get(crop)
    if expected and sorted(counts) != sorted(expected):
        raise ValueError(
            f"{crop} dataset classes differ from expected classes. "
            f"missing={sorted(set(expected) - set(counts))}, extra={sorted(set(counts) - set(expected))}"
        )

    empty_classes = [name for name, count in counts.items() if count == 0]
    small_classes = [name for name, count in counts.items() if count < min_images]

    if len(counts) < 2:
        raise ValueError(f"Need at least 2 class folders in {dataset_dir}")
    if empty_classes:
        raise ValueError(f"Empty class folders in {dataset_dir}: {empty_classes}")
    if small_classes:
        raise ValueError(f"Classes below minimum image count ({min_images}) in {dataset_dir}: {small_classes}")
    if sum(counts.values()) < 30:
        raise ValueError(
            f"Dataset is too small for training: {sum(counts.values())} images in {dataset_dir}"
        )

    return counts


def make_datasets(dataset_dir: Path, image_size: int, batch_size: int, seed: int):
    train_ds = tf.keras.utils.image_dataset_from_directory(
        dataset_dir,
        validation_split=0.2,
        subset="training",
        seed=seed,
        image_size=(image_size, image_size),
        batch_size=batch_size,
        shuffle=True,
    )

    val_ds = tf.keras.utils.image_dataset_from_directory(
        dataset_dir,
        validation_split=0.2,
        subset="validation",
        seed=seed,
        image_size=(image_size, image_size),
        batch_size=batch_size,
        shuffle=True,
    )

    return train_ds, val_ds, train_ds.class_names


def dataset_label_distribution(dataset, class_names: list[str]) -> dict[str, int]:
    counts = {class_name: 0 for class_name in class_names}
    file_paths = getattr(dataset, "file_paths", None)
    if file_paths:
        class_name_set = set(class_names)
        for file_path in file_paths:
            class_name = Path(file_path).parent.name
            if class_name in class_name_set:
                counts[class_name] += 1
        return counts

    for _, labels in dataset:
        for label in labels.numpy().astype(int).tolist():
            counts[class_names[label]] += 1
    return counts


def validate_split_integrity(train_ds, val_ds, class_names: list[str], crop: str) -> tuple[dict[str, int], dict[str, int]]:
    train_counts = dataset_label_distribution(train_ds, class_names)
    val_counts = dataset_label_distribution(val_ds, class_names)
    print(f"Train distribution for {crop}: {train_counts}")
    print(f"Validation distribution for {crop}: {val_counts}")

    missing_train = [name for name, count in train_counts.items() if count == 0]
    missing_val = [name for name, count in val_counts.items() if count == 0]
    if missing_train or missing_val:
        raise ValueError(f"{crop} split integrity failed. missing_train={missing_train}, missing_validation={missing_val}")
    return train_counts, val_counts


def compute_class_weights(counts: dict[str, int], class_names: list[str]) -> dict[int, float]:
    total = sum(counts.values())
    num_classes = len(class_names)

    return {
        index: total / (num_classes * max(counts[class_name], 1))
        for index, class_name in enumerate(class_names)
    }


def build_model(num_classes: int, image_size: int, dropout: float) -> tf.keras.Model:
    inputs = layers.Input(shape=(image_size, image_size, 3), name="image")

    x = layers.RandomFlip("horizontal", name="aug_flip")(inputs)
    x = layers.RandomRotation(0.08, name="aug_rotation")(x)
    x = layers.RandomZoom(0.12, name="aug_zoom")(x)
    x = layers.RandomContrast(0.12, name="aug_contrast")(x)
    x = layers.Rescaling(1.0 / 127.5, offset=-1.0, name="mobilenetv2_preprocess")(x)

    base_model = MobileNetV2(
        input_shape=(image_size, image_size, 3),
        include_top=False,
        weights="imagenet",
        input_tensor=x,
    )
    base_model.trainable = False

    x = layers.GlobalAveragePooling2D(name="avg_pool")(base_model.output)
    x = layers.BatchNormalization(name="head_bn")(x)
    x = layers.Dropout(dropout, name="head_dropout")(x)
    x = layers.Dense(128, activation="relu", kernel_regularizer=tf.keras.regularizers.l2(1e-4), name="head_dense")(x)
    x = layers.Dropout(dropout, name="head_dropout_2")(x)
    outputs = layers.Dense(num_classes, activation="softmax", name="predictions")(x)

    return models.Model(inputs=inputs, outputs=outputs, name="agromind_mobilenetv2")


def compile_model(model: tf.keras.Model, learning_rate: float) -> None:
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=["accuracy"],
    )


def make_callbacks(model_path: Path):
    return [
        ModelCheckpoint(model_path, monitor="val_accuracy", mode="max", save_best_only=True, verbose=1),
        EarlyStopping(monitor="val_loss", patience=6, restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor="val_loss", factor=0.3, patience=3, min_lr=1e-7, verbose=1),
    ]


def unfreeze_for_fine_tuning(model: tf.keras.Model, train_last_layers: int) -> None:
    try:
        avg_pool_index = next(index for index, layer in enumerate(model.layers) if layer.name == "avg_pool")
    except StopIteration:
        return

    base_layers = [
        layer
        for layer in model.layers[:avg_pool_index]
        if not layer.name.startswith(("aug_", "mobilenetv2_preprocess"))
    ]

    for layer in base_layers[:-train_last_layers]:
        layer.trainable = False
    for layer in base_layers[-train_last_layers:]:
        layer.trainable = True
    for layer in base_layers:
        if isinstance(layer, layers.BatchNormalization):
            layer.trainable = False


def evaluate_model(model: tf.keras.Model, val_ds, class_names: list[str], output_dir: Path) -> dict:
    y_true = []
    y_pred = []

    for images, labels in val_ds:
        probs = model(images, training=False).numpy()
        y_true.extend(labels.numpy().astype(int).tolist())
        y_pred.extend(np.argmax(probs, axis=1).astype(int).tolist())

    matrix = tf.math.confusion_matrix(y_true, y_pred, num_classes=len(class_names)).numpy()
    metrics = {}

    for index, class_name in enumerate(class_names):
        tp = matrix[index, index]
        fp = matrix[:, index].sum() - tp
        fn = matrix[index, :].sum() - tp
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-12)
        metrics[class_name] = {
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1": round(float(f1), 4),
            "support": int(matrix[index, :].sum()),
        }

    zero_support = [class_name for class_name, metric in metrics.items() if metric["support"] == 0]
    if zero_support:
        raise ValueError(f"Evaluation failed because classes have zero validation support: {zero_support}")

    with (output_dir / "confusion_matrix.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["actual/predicted", *class_names])
        for class_name, row in zip(class_names, matrix):
            writer.writerow([class_name, *row.tolist()])

    with (output_dir / "classification_report.json").open("w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)

    return {
        "confusion_matrix": matrix.tolist(),
        "per_class": metrics,
    }


def save_metadata(
    crop: str,
    model_path: Path,
    class_names: list[str],
    image_size: int,
    counts: dict[str, int],
    evaluation: dict,
    train_distribution: dict[str, int],
    validation_distribution: dict[str, int],
    validation_accuracy: float,
) -> None:
    expected_count = EXPECTED_CLASS_COUNTS.get(crop)
    if expected_count is not None and len(class_names) != expected_count:
        raise ValueError(
            f"{crop} dataset produced {len(class_names)} classes, expected {expected_count}: {class_names}"
        )

    CLASS_NAMES_DIR.mkdir(parents=True, exist_ok=True)
    with (CLASS_NAMES_DIR / f"{crop}_classes.json").open("w", encoding="utf-8") as file:
        json.dump({
            "crop": crop,
            "class_names": class_names,
            "class_count": len(class_names),
            "dataset_counts": counts,
            "image_size": [image_size, image_size],
            "training_date": datetime.now(timezone.utc).isoformat(),
            "validation_accuracy": validation_accuracy,
        }, file, indent=2)

    metadata = {
        "crop": crop,
        "model_file": model_path.name,
        "class_names": class_names,
        "class_count": len(class_names),
        "image_size": [image_size, image_size],
        "input_scale": "model_includes_mobilenetv2_rescaling_-1_to_1",
        "temperature": 1.0,
        "dataset_counts": counts,
        "train_distribution": train_distribution,
        "validation_distribution": validation_distribution,
        "validation_accuracy": validation_accuracy,
        "evaluation": evaluation,
    }

    with model_path.with_suffix(".json").open("w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)


def train(args) -> None:
    set_reproducibility(args.seed)
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)

    dataset_dir = DATASETS_DIR / args.crop
    counts = validate_dataset(args.crop, dataset_dir, args.min_images_per_class)
    print(f"Dataset counts for {args.crop}: {counts}")

    train_ds, val_ds, class_names = make_datasets(dataset_dir, args.image_size, args.batch_size, args.seed)
    train_distribution, validation_distribution = validate_split_integrity(train_ds, val_ds, class_names, args.crop)
    class_weights = compute_class_weights(counts, class_names)
    print(f"Class order: {class_names}")
    print(f"Class weights: {class_weights}")

    autotune = tf.data.AUTOTUNE
    train_ds = train_ds.prefetch(autotune)
    val_ds = val_ds.prefetch(autotune)

    model_path = TRAINING_DIR / f"{args.crop}_model.keras"
    legacy_model_path = TRAINING_DIR / f"{args.crop}_model.h5"

    model = build_model(len(class_names), args.image_size, args.dropout)
    compile_model(model, args.learning_rate)

    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs,
        class_weight=class_weights,
        callbacks=make_callbacks(model_path),
    )

    if args.fine_tune_epochs > 0:
        unfreeze_for_fine_tuning(model, args.train_last_layers)
        compile_model(model, args.fine_tune_learning_rate)
        fine_tune_history = model.fit(
            train_ds,
            validation_data=val_ds,
            epochs=args.epochs + args.fine_tune_epochs,
            initial_epoch=args.epochs,
            class_weight=class_weights,
            callbacks=make_callbacks(model_path),
        )
        for key, values in fine_tune_history.history.items():
            history.history.setdefault(key, []).extend(values)

    output_neurons = int(model.output_shape[-1])
    if output_neurons != len(class_names):
        raise ValueError(f"{args.crop} saved model output neurons {output_neurons} != class count {len(class_names)}")

    evaluation = evaluate_model(model, val_ds, class_names, TRAINING_DIR)
    validation_accuracy = float(max(history.history.get("val_accuracy", [0.0])))
    (TRAINING_DIR / f"{args.crop}_training_history.json").write_text(json.dumps(history.history, indent=2), encoding="utf-8")
    save_metadata(args.crop, model_path, class_names, args.image_size, counts, evaluation, train_distribution, validation_distribution, validation_accuracy)

    if args.save_h5:
        model.save(legacy_model_path)
        save_metadata(args.crop, legacy_model_path, class_names, args.image_size, counts, evaluation, train_distribution, validation_distribution, validation_accuracy)

    print(f"Saved model: {model_path}")
    print(f"Saved metadata: {model_path.with_suffix('.json')}")
    print(f"Saved class names: {CLASS_NAMES_DIR / f'{args.crop}_classes.json'}")
    print(f"Saved confusion matrix: {TRAINING_DIR / 'confusion_matrix.csv'}")
    print("TRAINING SUMMARY")
    print(f"Crop: {args.crop}")
    print(f"Detected Classes: {class_names}")
    print(f"Image Count: {sum(counts.values())}")
    print(f"Output Neurons: {output_neurons}")
    print(f"Validation Accuracy: {validation_accuracy:.4f}")
    print(f"Class Count Match: {output_neurons == len(class_names)}")
    print("Deployment Ready: YES")


def parse_args():
    parser = argparse.ArgumentParser(description="Train AgroMind crop disease classifier.")
    parser.add_argument("--crop", choices=SUPPORTED_CROPS, default="tomato")
    parser.add_argument("--image-size", type=int, default=IMG_SIZE)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--epochs", type=int, default=INITIAL_EPOCHS)
    parser.add_argument("--fine-tune-epochs", type=int, default=FINE_TUNE_EPOCHS)
    parser.add_argument("--train-last-layers", type=int, default=35)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--fine-tune-learning-rate", type=float, default=1e-5)
    parser.add_argument("--dropout", type=float, default=0.35)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--save-h5", action="store_true", help="Also save a legacy .h5 copy.")
    parser.add_argument("--min-images-per-class", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    train(parse_args())
