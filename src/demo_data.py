"""Build a transparent demonstration bundle from real demand and scenario assumptions."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.business_intelligence import average_daily_demand
from src.data_pipeline import ROOT
from src.real_demand import TRAIN_PATH


DEMO_DIRECTORY = ROOT / "data" / "demo"
DEMO_METADATA = DEMO_DIRECTORY / "README_DEMO.json"
LOT_SCENARIOS = ((4, 4), (4, 6), (4, 10), (4, 20), (4, 40), (1, 4), (7, 10), (2, 50))
DEMO_COLUMN_UNITS: dict[str, dict[str, str]] = {
    "sales": {"quantity": "unidades"},
    "inventory": {
        "on_hand_units": "unidades",
        "unit_cost": "€/unidad",
        "reorder_lead_days": "días",
        "minimum_stock": "unidades",
    },
    "costs": {
        "unit_cost": "€/unidad",
        "unit_price": "€/unidad",
        "holding_cost_per_unit_day": "€/unidad/día",
    },
    "lots": {"stock_available": "unidades", "unit_cost": "€/unidad"},
}


def build_demo_bundle(
    train_data: pd.DataFrame | None = None,
    output_directory: Path = DEMO_DIRECTORY,
) -> dict[str, Path]:
    """Create company-shaped demo CSVs from real or explicitly supplied training rows."""
    columns = ["store_id", "product_id", "dt", "sale_amount", "discount", "holiday_flag"]
    train = (
        pd.read_parquet(TRAIN_PATH, columns=columns)
        if train_data is None
        else train_data.copy()
    )
    missing_columns = set(columns) - set(train.columns)
    if missing_columns:
        raise ValueError(f"Faltan columnas para generar la demo: {', '.join(sorted(missing_columns))}.")
    train = train.loc[:, columns].copy()
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
    output_directory.mkdir(parents=True, exist_ok=True)

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
        latest_date=("date", "max"),
    )
    products = products.merge(
        average_daily_demand(sales, assume_complete_period=True).rename(
            columns={"quantity": "average_daily_demand"}
        ),
        on="product_id",
        how="left",
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
    scenarios = pd.DataFrame(LOT_SCENARIOS[: len(products)], columns=["expiry_days", "stock_cover_days"])
    expiry_dates = (
        pd.to_datetime(products["latest_date"]).reset_index(drop=True)
        + pd.to_timedelta(scenarios["expiry_days"], unit="D")
    ).dt.date.astype(str)
    lots = pd.DataFrame(
        {
            "lot_id": [f"FRN-DEMO-LOT-{index:03}" for index in range(1, len(products) + 1)],
            "product_id": products["product_id"].reset_index(drop=True),
            "stock_available": (
                products["average_daily_demand"].reset_index(drop=True)
                * scenarios["stock_cover_days"]
            ).round(2).clip(lower=1),
            "expiry_date": expiry_dates,
            "unit_cost": 2.40,
            "store_id": store_id,
        }
    )
    paths = {
        "sales": output_directory / "ventas_demanda_real_demo.csv",
        "inventory": output_directory / "inventario_escenario_demo.csv",
        "costs": output_directory / "costes_escenario_demo.csv",
        "lots": output_directory / "lotes_escenario_demo.csv",
    }
    sales.to_csv(paths["sales"], index=False)
    inventory.to_csv(paths["inventory"], index=False)
    costs.to_csv(paths["costs"], index=False)
    lots.to_csv(paths["lots"], index=False)
    (output_directory / DEMO_METADATA.name).write_text(
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
                    "lots": "Lot stock cover and expiry dates vary by lot to demonstrate distinct risk levels.",
                },
                "column_units": DEMO_COLUMN_UNITS,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return paths


if __name__ == "__main__":
    print({name: str(path) for name, path in build_demo_bundle().items()})
