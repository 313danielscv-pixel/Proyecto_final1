"""Build a transparent demonstration bundle from real demand and scenario assumptions."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.data_pipeline import ROOT
from src.real_demand import TRAIN_PATH


DEMO_DIRECTORY = ROOT / "data" / "demo"
DEMO_METADATA = DEMO_DIRECTORY / "README_DEMO.json"


def build_demo_bundle() -> dict[str, Path]:
    """Create company-shaped demo CSVs from several real products at one store."""
    columns = ["store_id", "product_id", "dt", "sale_amount", "discount", "holiday_flag"]
    train = pd.read_parquet(TRAIN_PATH, columns=columns)
    train["dt"] = pd.to_datetime(train["dt"])
    product_history = train.groupby(["store_id", "product_id"], as_index=False).agg(
        observed_days=("dt", "nunique"),
        total_units=("sale_amount", "sum"),
    )
    eligible_history = product_history.loc[product_history["observed_days"] >= 30]
    if eligible_history.empty:
        raise ValueError("La fuente no tiene productos con al menos 30 días de ventas para la demostración.")
    products_per_store = eligible_history.groupby("store_id")["product_id"].nunique()
    selected_store_id = products_per_store.sort_values(ascending=False).index[0]
    selected_products = (
        eligible_history.loc[eligible_history["store_id"] == selected_store_id]
        .sort_values(["total_units", "product_id"], ascending=[False, True])
        .head(8)
    )
    series = train.loc[
        (train["store_id"] == selected_store_id)
        & train["product_id"].isin(selected_products["product_id"])
    ].copy()
    series = series.sort_values(["product_id", "dt"]).reset_index(drop=True)
    product_labels = {
        product_id: f"FRN-{int(product_id)}"
        for product_id in selected_products["product_id"]
    }
    series["product_id"] = series["product_id"].map(product_labels)
    store_id = f"FRN-STORE-{int(selected_store_id)}"
    DEMO_DIRECTORY.mkdir(parents=True, exist_ok=True)

    sales = pd.DataFrame(
        {
            "date": series["dt"].dt.date.astype(str),
            "product_id": series["product_id"],
            "quantity": series["sale_amount"],
            "store_id": store_id,
            "category": "fresh_retail_demo",
            "promotion": series["discount"].lt(1),
        }
    )
    products = sales.groupby("product_id", as_index=False).agg(
        average_daily_demand=("quantity", "mean"),
        latest_date=("date", "max"),
    )
    inventory = pd.DataFrame(
        {
            "snapshot_date": products["latest_date"],
            "product_id": products["product_id"],
            "on_hand_units": (products["average_daily_demand"] * 18).round(2).clip(lower=1),
            "unit_cost": 2.40,
            "reorder_lead_days": 5,
            "minimum_stock": (products["average_daily_demand"] * 5).round(2).clip(lower=1),
            "store_id": store_id,
            "expiry_date": "",
        }
    )
    costs = pd.DataFrame(
        {
            "effective_date": products["latest_date"],
            "product_id": products["product_id"],
            "unit_cost": 2.40,
            "unit_price": 4.80,
            "holding_cost_per_unit_day": 0.03,
        }
    )
    expiry_dates = (
        pd.to_datetime(products["latest_date"]) + pd.Timedelta(days=4)
    ).dt.date.astype(str)
    lots = pd.DataFrame(
        {
            "lot_id": [f"FRN-DEMO-LOT-{index:03}" for index in range(1, len(products) + 1)],
            "product_id": products["product_id"],
            "stock_available": (products["average_daily_demand"] * 10).round(2).clip(lower=1),
            "expiry_date": expiry_dates,
            "unit_cost": 2.40,
            "store_id": store_id,
        }
    )
    paths = {
        "sales": DEMO_DIRECTORY / "ventas_demanda_real_demo.csv",
        "inventory": DEMO_DIRECTORY / "inventario_escenario_demo.csv",
        "costs": DEMO_DIRECTORY / "costes_escenario_demo.csv",
        "lots": DEMO_DIRECTORY / "lotes_escenario_demo.csv",
    }
    sales.to_csv(paths["sales"], index=False)
    inventory.to_csv(paths["inventory"], index=False)
    costs.to_csv(paths["costs"], index=False)
    lots.to_csv(paths["lots"], index=False)
    DEMO_METADATA.write_text(
        json.dumps(
            {
                "real_source": "FreshRetailNet-50K by Dingdong Inc., CC BY 4.0",
                "source_url": "https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K",
                "real_fields": ["date", "product_id", "quantity", "store_id", "promotion"],
                "selected_store": store_id,
                "selected_product_count": int(products["product_id"].nunique()),
                "scenario_fields": {
                    "inventory": "Stock, lead time and safety stock are demonstration assumptions.",
                    "costs": "Unit cost, price and holding cost are demonstration assumptions.",
                    "lots": "Lot stock and expiry date are demonstration assumptions.",
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return paths


if __name__ == "__main__":
    print({name: str(path) for name, path in build_demo_bundle().items()})
