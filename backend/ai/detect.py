import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
YOLO_MODEL_PATH = BASE_DIR / "yolov8n.pt"

RESULTS_FOLDER = BASE_DIR / "results"

os.makedirs(RESULTS_FOLDER, exist_ok=True)

model = None


def load_yolo_model():
    global model

    if model is None:
        from ultralytics import YOLO

        if not YOLO_MODEL_PATH.exists():
            raise FileNotFoundError(f"YOLO model not found: {YOLO_MODEL_PATH}")
        model = YOLO(str(YOLO_MODEL_PATH))

    return model


def detect_objects(image_path):
    yolo_model = load_yolo_model()

    results = yolo_model(image_path)

    detections = []

    result_image_path = None

    for result in results:

        boxes = result.boxes

        for box in boxes:

            class_id = int(box.cls[0])
            confidence = float(box.conf[0])

            detections.append({
                "class_name": yolo_model.names[class_id],
                "confidence": round(confidence, 2)
            })

        # Save result image with bounding boxes
        output_path = os.path.join(
            str(RESULTS_FOLDER),
            f"result_{os.path.basename(image_path)}"
        )

        result.save(filename=output_path)

        result_image_path = output_path

    return detections, result_image_path
