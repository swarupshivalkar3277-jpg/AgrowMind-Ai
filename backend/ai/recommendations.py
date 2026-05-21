from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
RECOMMENDATIONS_PATH = BASE_DIR / "data" / "recommendations.json"


def normalize_key(value: str | None) -> str:
    return (value or "").strip().lower().replace(" ", "_")


@lru_cache(maxsize=1)
def load_recommendations() -> dict:
    with RECOMMENDATIONS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def recommendation_for(crop: str, disease: str) -> dict:
    data = load_recommendations()
    crop_key = normalize_key(crop)
    disease_key = normalize_key(disease)

    crop_data = data.get(crop_key, {})
    recommendation = crop_data.get(disease_key) or data.get("default", {})

    return {
        "severity": recommendation.get("severity", "Medium"),
        "fertilizer": recommendation.get("fertilizer", []),
        "treatment": recommendation.get("treatment", []),
        "irrigation": recommendation.get("irrigation", ""),
        "prevention": recommendation.get("prevention", []),
        "organic_solution": recommendation.get("organic_solution", []),
        "harvest_risk": recommendation.get("harvest_risk", "Moderate"),
    }


def enrich_prediction(crop: str, prediction: dict) -> dict:
    if not isinstance(prediction, dict) or "error" in prediction:
        return prediction

    disease = prediction.get("disease") or prediction.get("prediction")
    recommendations = recommendation_for(crop, disease)

    return {
        **prediction,
        **recommendations,
    }
