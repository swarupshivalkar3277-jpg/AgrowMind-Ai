from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
RECOMMENDATIONS_PATH = BASE_DIR / "data" / "recommendations.json"


def normalize_key(value: str | None) -> str:
    normalized = (value or "").strip()
    if "___" in normalized:
        normalized = normalized.split("___", 1)[1]
    normalized = normalized.replace("-", " ")
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", normalized.lower())
    return re.sub(r"_+", "_", normalized).strip("_")


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

    display_name = recommendation.get("display_name") or disease.replace("_", " ").strip().title()
    severity = recommendation.get("severity", "Medium")

    return {
        "display_name": display_name,
        "description": recommendation.get("description") or f"{display_name} detected in {crop}. Confirm symptoms in the field before applying treatments.",
        "severity": severity,
        "fertilizer": recommendation.get("fertilizer", []),
        "symptoms": recommendation.get("symptoms", []),
        "causes": recommendation.get("causes", []),
        "treatment": recommendation.get("treatment", []),
        "chemical_solutions": recommendation.get("chemical_solutions", []),
        "irrigation": recommendation.get("irrigation", ""),
        "prevention": recommendation.get("prevention", []),
        "organic_solutions": recommendation.get("organic_solutions", recommendation.get("organic_solution", [])),
        "recommended_products": recommendation.get("recommended_products", []),
        "harvest_risk": recommendation.get("harvest_risk", "Moderate"),
        "recovery_expectations": recommendation.get("recovery_expectations") or ("7-14 days with timely care" if severity != "High" else "14-21 days; monitor closely and escalate if spread continues"),
    }


def validate_recommendation_coverage(crop: str, class_names: list[str]) -> list[str]:
    data = load_recommendations()
    crop_key = normalize_key(crop)
    crop_data = data.get(crop_key, {})
    missing = []

    required_fields = {"display_name", "severity", "symptoms", "causes", "treatment", "prevention"}
    for class_name in class_names:
        disease_key = normalize_key(class_name)
        recommendation = crop_data.get(disease_key)
        if not recommendation or required_fields - set(recommendation):
            missing.append(class_name)

    return missing


def enrich_prediction(crop: str, prediction: dict) -> dict:
    if not isinstance(prediction, dict) or "error" in prediction:
        return prediction

    disease = prediction.get("disease") or prediction.get("prediction")
    recommendations = recommendation_for(crop, disease)
    recommendation_payload = {
        "severity": recommendations["severity"],
        "symptoms": recommendations["symptoms"],
        "causes": recommendations["causes"],
        "treatment": recommendations["treatment"],
        "organic_solutions": recommendations["organic_solutions"],
        "chemical_solutions": recommendations["chemical_solutions"],
        "prevention": recommendations["prevention"],
        "recommended_products": recommendations["recommended_products"],
        "description": recommendations["description"],
        "recovery_expectations": recommendations["recovery_expectations"],
    }

    return {
        **prediction,
        "class_name": disease,
        "disease": recommendations["display_name"],
        **recommendations,
        "organic_solution": recommendations["organic_solutions"],
        "recommendation": recommendation_payload,
        "recommendations": recommendation_payload,
    }
