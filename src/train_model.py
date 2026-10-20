"""Train and evaluate the ResQData waste-risk classifier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, classification_report, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src.data_pipeline import DEFAULT_OUTPUT, ROOT, run_pipeline


MODEL_PATH = ROOT / "models" / "waste_risk_model.joblib"
METRICS_PATH = ROOT / "data" / "processed" / "model_metrics.json"
FEATURE_COLUMNS = [
    "tienda_nombre",
    "tipo_ubicacion",
    "categoria",
    "dias_vida_util",
    "dias_restantes",
    "unidades_recibidas",
    "stock_estimado",
    "velocidad_venta_diaria",
    "precio_venta_base",
    "coste_unitario",
    "dia_semana",
]
CATEGORICAL_COLUMNS = ["tienda_nombre", "tipo_ubicacion", "categoria", "dia_semana"]
NUMERIC_COLUMNS = [column for column in FEATURE_COLUMNS if column not in CATEGORICAL_COLUMNS]


def create_model() -> Pipeline:
    """Create a deterministic pipeline suitable for mixed operational features."""
    preprocess = ColumnTransformer(
        transformers=[
            ("numeric", Pipeline([("imputer", SimpleImputer(strategy="median"))]), NUMERIC_COLUMNS),
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                CATEGORICAL_COLUMNS,
            ),
        ]
    )
    return Pipeline(
        steps=[
            ("preprocess", preprocess),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=300,
                    min_samples_leaf=3,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def train_and_evaluate(
    snapshots_path: Path = DEFAULT_OUTPUT,
    model_path: Path = MODEL_PATH,
    metrics_path: Path = METRICS_PATH,
) -> dict[str, object]:
    """Fit a group-safe holdout model and write the model and validation metrics."""
    if not snapshots_path.exists():
        run_pipeline(output_path=snapshots_path)

    snapshots = pd.read_csv(snapshots_path)
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    train_index, test_index = next(
        splitter.split(snapshots[FEATURE_COLUMNS], snapshots["hubo_merma"], groups=snapshots["lote_id"])
    )
    train = snapshots.iloc[train_index]
    test = snapshots.iloc[test_index]

    model = create_model()
    model.fit(train[FEATURE_COLUMNS], train["hubo_merma"])
    probabilities = model.predict_proba(test[FEATURE_COLUMNS])[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    report = classification_report(test["hubo_merma"], predictions, output_dict=True, zero_division=0)
    metrics = {
        "validation_strategy": "GroupShuffleSplit by lote_id; all snapshots of a lot remain in one partition",
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_lots": int(train["lote_id"].nunique()),
        "test_lots": int(test["lote_id"].nunique()),
        "positive_rate_test": round(float(test["hubo_merma"].mean()), 4),
        "roc_auc": round(float(roc_auc_score(test["hubo_merma"], probabilities)), 4),
        "average_precision": round(float(average_precision_score(test["hubo_merma"], probabilities)), 4),
        "precision": round(float(report["1"]["precision"]), 4),
        "recall": round(float(report["1"]["recall"]), 4),
        "f1": round(float(report["1"]["f1-score"]), 4),
        "threshold": 0.5,
        "data_limitation": "Metrics are from a synthetic pilot and cannot be interpreted as production performance.",
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURE_COLUMNS}, model_path)
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train ResQData waste-risk classifier.")
    parser.add_argument("--snapshots", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", type=Path, default=MODEL_PATH)
    parser.add_argument("--metrics", type=Path, default=METRICS_PATH)
    arguments = parser.parse_args()
    print(json.dumps(train_and_evaluate(arguments.snapshots, arguments.model, arguments.metrics), indent=2))
