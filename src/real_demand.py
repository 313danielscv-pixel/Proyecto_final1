"""Prepare and evaluate a real-data demand baseline from FreshRetailNet-50K."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.data_pipeline import ROOT


SOURCE_URL = "https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K"
TRAIN_PATH = ROOT / "data" / "external" / "freshretailnet" / "train.parquet"
EVAL_PATH = ROOT / "data" / "external" / "freshretailnet" / "eval.parquet"
FORECAST_PATH = ROOT / "data" / "processed" / "freshretailnet_forecasts.csv"
METRICS_PATH = ROOT / "data" / "processed" / "freshretailnet_metrics.json"


def build_real_demand_demo(max_series: int = 100) -> dict[str, float | int | str]:
    """Evaluate a seven-day seasonal-naive demand baseline on real held-out observations."""
    train = pd.read_parquet(TRAIN_PATH, columns=["store_id", "product_id", "dt", "sale_amount", "discount", "holiday_flag"])
    evaluation = pd.read_parquet(EVAL_PATH, columns=["store_id", "product_id", "dt", "sale_amount", "discount", "holiday_flag"])
    keys = train[["store_id", "product_id"]].drop_duplicates().sort_values(["store_id", "product_id"]).head(max_series)
    train = train.merge(keys, on=["store_id", "product_id"])
    evaluation = evaluation.merge(keys, on=["store_id", "product_id"])
    combined = pd.concat([train.assign(split="train"), evaluation.assign(split="evaluation")], ignore_index=True)
    combined["dt"] = pd.to_datetime(combined["dt"])
    combined = combined.sort_values(["store_id", "product_id", "dt"])
    combined["forecast_units"] = combined.groupby(["store_id", "product_id"])["sale_amount"].shift(7)
    forecasts = combined.loc[combined["split"].eq("evaluation")].dropna(subset=["forecast_units"]).copy()
    metrics = {
        "dataset": "FreshRetailNet-50K",
        "license": "CC BY 4.0",
        "source_url": SOURCE_URL,
        "evaluation_method": "Seasonal naive: sales from seven days earlier; 100 deterministic store-product series.",
        "evaluation_rows": int(len(forecasts)),
        "mae": round(float(mean_absolute_error(forecasts["sale_amount"], forecasts["forecast_units"])), 4),
        "rmse": round(float(mean_squared_error(forecasts["sale_amount"], forecasts["forecast_units"]) ** 0.5), 4),
    }
    FORECAST_PATH.parent.mkdir(parents=True, exist_ok=True)
    forecasts.to_csv(FORECAST_PATH, index=False)
    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    print(json.dumps(build_real_demand_demo(), ensure_ascii=False, indent=2))
