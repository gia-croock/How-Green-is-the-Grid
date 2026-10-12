import json
import math
from typing import Any

MODEL_PATH = "waiting_model.json"


def load_model() -> dict[str, Any]:
    """Load the exported logistic regression parameters."""
    with open(MODEL_PATH, encoding="utf-8") as file:
        return json.load(file)


def predict(features: dict[str, float], model: dict[str, Any]) -> dict[str, Any]:
    """Predict whether the next hour is likely to be cleaner."""
    score = model["intercept"]

    for name, mean, std, weight in zip(
        model["features"],
        model["means"],
        model["stds"],
        model["weights"],
    ):
        score += weight * ((features[name] - mean) / std)

    probability = 1 / (1 + math.exp(-score))

    return {
        "recommendation": "likely_cleaner" if probability >= 0.5 else "likely_worse",
        "probability": round(probability, 3),
    }


if __name__ == "__main__":
    # Example: 18:00, not green at 30% and falling.
    hour = 18
    example = {
        "not_green": 30.0,
        "change_30m": -1.5,
        "change_2h": -4.0,
        "hour_sin": math.sin(2 * math.pi * hour / 24),
        "hour_cos": math.cos(2 * math.pi * hour / 24),
    }
    print(predict(example, load_model()))
