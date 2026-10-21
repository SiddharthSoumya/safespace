from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

from backend.core.config import get_settings

settings = get_settings()

HIGH_SEVERITY_TERMS = {
    "assault", "hit", "slap", "touch", "grab", "threat", "rape", "stalk", "blackmail", "forced", "violence"
}
MEDIUM_SEVERITY_TERMS = {
    "abuse", "humiliate", "insult", "mock", "harass", "bully", "shout", "yell", "message", "email", "late night"
}


@lru_cache(maxsize=1)
def load_model() -> Any:
    model_path = Path(settings.model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"Classifier artifact not found: {model_path}")
    return joblib.load(model_path)


def classify_text(text: str) -> tuple[str, float]:
    model = load_model()
    probabilities = model.predict_proba([text])[0]
    classes = list(model.classes_)
    best_index = int(probabilities.argmax())
    return classes[best_index], float(probabilities[best_index])


def infer_severity(text: str, confidence: float) -> str:
    lowered = text.lower()
    if any(term in lowered for term in HIGH_SEVERITY_TERMS):
        return "HIGH"
    if any(term in lowered for term in MEDIUM_SEVERITY_TERMS):
        return "MEDIUM"
    if confidence >= 0.80:
        return "MEDIUM"
    return "LOW"
