"""Prepare and compare demand forecasts on FreshRetailNet-50K."""

from __future__ import annotations

import json

import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.data_pipeline import ROOT


SOURCE_URL = "https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K"
TRAIN_PATH = ROOT / "data" / "external" / "freshretailnet" / "train.parquet"
EVAL_PATH = ROOT / "data" / "external" / "freshretailnet" / "eval.parquet"
FORECAST_PATH = ROOT / "data" / "processed" / "freshretailnet_forecasts.csv"
METRICS_PATH = ROOT / "data" / "processed" / "freshretailnet_metrics.json"


def evaluate_demand_models(
    train: pd.DataFrame,
    evaluation: pd.DataFrame,
    max_series: int = 100,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Compare a seasonal-naive baseline with a fixed-origin seven-day moving average."""
    if max_series < 1:
        raise ValueError("max_series debe ser al menos 1.")

    required = {"store_id", "product_id", "dt", "sale_amount"}
    for name, frame in (("entrenamiento", train), ("evaluación", evaluation)):
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Faltan columnas de {name}: {', '.join(sorted(missing))}.")

    def clean_daily_sales(frame: pd.DataFrame) -> pd.DataFrame:
        cleaned = frame.loc[:, ["store_id", "product_id", "dt", "sale_amount"]].copy()
        cleaned["dt"] = pd.to_datetime(cleaned["dt"], errors="coerce").dt.normalize()
        cleaned["sale_amount"] = pd.to_numeric(cleaned["sale_amount"], errors="coerce")
        cleaned = cleaned.dropna(subset=["store_id", "product_id", "dt", "sale_amount"])
        return (
            cleaned.groupby(["store_id", "product_id", "dt"], as_index=False)["sale_amount"]
            .sum()
            .sort_values(["store_id", "product_id", "dt"])
        )

    train = clean_daily_sales(train)
    evaluation = clean_daily_sales(evaluation)
    keys = (
        train.groupby(["store_id", "product_id"])
        .size()
        .loc[lambda counts: counts >= 7]
        .rename("training_days")
        .reset_index()[["store_id", "product_id"]]
        .merge(evaluation[["store_id", "product_id"]].drop_duplicates(), on=["store_id", "product_id"])
        .sort_values(["store_id", "product_id"])
        .head(max_series)
    )
    if keys.empty:
        raise ValueError("No hay series con al menos 7 días de entrenamiento y datos de evaluación.")

    train = train.merge(keys, on=["store_id", "product_id"])
    evaluation = evaluation.merge(keys, on=["store_id", "product_id"])
    moving_averages = (
        train.groupby(["store_id", "product_id"], group_keys=False)
        .tail(7)
        .groupby(["store_id", "product_id"], as_index=False)["sale_amount"]
        .mean()
        .rename(columns={"sale_amount": "moving_average_7d_units"})
    )
    combined = pd.concat(
        [train.assign(split="train"), evaluation.assign(split="evaluation")],
        ignore_index=True,
    ).sort_values(["store_id", "product_id", "dt"])
    combined["forecast_units"] = combined.groupby(["store_id", "product_id"])["sale_amount"].shift(7)
    combined = combined.merge(moving_averages, on=["store_id", "product_id"], how="left")
    forecasts = combined.loc[combined["split"].eq("evaluation")].dropna(
        subset=["forecast_units", "moving_average_7d_units"]
    ).copy()
    if forecasts.empty:
        raise ValueError("No hay filas evaluables para comparar los modelos.")

    model_columns = {
        "seasonal_naive": "forecast_units",
        "moving_average_7d": "moving_average_7d_units",
    }
    model_metrics: dict[str, dict[str, float]] = {}
    for model_name, prediction_column in model_columns.items():
        model_metrics[model_name] = {
            "mae": round(float(mean_absolute_error(forecasts["sale_amount"], forecasts[prediction_column])), 4),
            "rmse": round(
                float(mean_squared_error(forecasts["sale_amount"], forecasts[prediction_column]) ** 0.5),
                4,
            ),
        }

    metrics = {
        "dataset": "FreshRetailNet-50K",
        "license": "CC BY 4.0",
        "source_url": SOURCE_URL,
        "evaluation_method": (
            "Holdout temporal de 7 días: referencia estacional (venta de hace 7 días) frente a media "
            "de los últimos 7 días de entrenamiento, constante durante el horizonte."
        ),
        "evaluation_rows": int(len(forecasts)),
        "series_evaluated": int(len(keys)),
        "models": model_metrics,
        "mae": model_metrics["seasonal_naive"]["mae"],
        "rmse": model_metrics["seasonal_naive"]["rmse"],
        "best_model_by_mae": min(model_metrics, key=lambda name: model_metrics[name]["mae"]),
    }
    return forecasts, metrics


def build_real_demand_demo(max_series: int = 100) -> dict[str, object]:
    """Evaluate both demand models on real held-out FreshRetailNet observations."""
    columns = ["store_id", "product_id", "dt", "sale_amount"]
    train = pd.read_parquet(TRAIN_PATH, columns=columns)
    evaluation = pd.read_parquet(EVAL_PATH, columns=columns)
    forecasts, metrics = evaluate_demand_models(train, evaluation, max_series=max_series)
    FORECAST_PATH.parent.mkdir(parents=True, exist_ok=True)
    forecasts.to_csv(FORECAST_PATH, index=False)
    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    print(json.dumps(build_real_demand_demo(), ensure_ascii=False, indent=2))
