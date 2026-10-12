import json
from typing import Any

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.preprocessing import StandardScaler

FEATURES = [
    "not_green",
    "change_30m",
    "change_2h",
    "hour_sin",
    "hour_cos",
]


def split_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train on historical data and reserve the final 30 days for testing."""
    test_start = df["timestamp"].max() - pd.Timedelta(days=30)
    return (
        df[df["timestamp"] < test_start],
        df[df["timestamp"] >= test_start],
    )


def train_model(df: pd.DataFrame) -> dict[str, Any]:
    """Fit logistic regression, evaluate it, and export inference parameters."""
    train, test = split_data(df)

    scaler = StandardScaler().fit(train[FEATURES])
    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(scaler.transform(train[FEATURES]), train["target"])

    probabilities = model.predict_proba(scaler.transform(test[FEATURES]))[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    y = test["target"]

    print(f"accuracy: {accuracy_score(y, predictions):.1%}")
    print(f"f1:       {f1_score(y, predictions):.2f}")

    return {
        "features": FEATURES,
        "means": scaler.mean_.tolist(),
        "stds": scaler.scale_.tolist(),
        "weights": model.coef_[0].tolist(),
        "intercept": float(model.intercept_[0]),
    }


def main() -> None:
    """Train on prepared data and save the model."""
    df = pd.read_csv("waiting_data.csv", parse_dates=["timestamp"])

    with open("waiting_model.json", "w", encoding="utf-8") as file:
        json.dump(train_model(df), file, indent=2)


if __name__ == "__main__":
    main()
