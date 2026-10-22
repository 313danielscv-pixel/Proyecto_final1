"""Explainable lot-risk calculations driven by a company's uploaded history."""

from __future__ import annotations

import pandas as pd

from src.business_intelligence import average_daily_demand


MINIMUM_SALES_DAYS = 30


def build_lot_risk(lots: pd.DataFrame, sales: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Estimate lot risk from observed product demand before each expiry date."""
    sales = sales.dropna(subset=["date", "product_id", "quantity"]).copy()
    sales["date"] = pd.to_datetime(sales["date"]).dt.normalize()
    active_days = sales.groupby("product_id")["date"].nunique()
    if active_days.empty or active_days.max() < MINIMUM_SALES_DAYS:
        return pd.DataFrame(), [
            f"Se necesitan al menos {MINIMUM_SALES_DAYS} días de ventas por producto para calcular riesgo por lote."
        ]

    reference_date = sales["date"].max().normalize()
    daily_demand = average_daily_demand(sales).rename(columns={"quantity": "daily_demand"})
    result = lots.merge(daily_demand, on="product_id", how="left")
    result["sales_days"] = result["product_id"].map(active_days).fillna(0).astype(int)
    warnings: list[str] = []
    insufficient = result["sales_days"] < MINIMUM_SALES_DAYS
    if insufficient.any():
        products = ", ".join(result.loc[insufficient, "product_id"].astype(str).unique()[:5])
        warnings.append(f"Sin historial suficiente para: {products}. Esos lotes no reciben una estimación.")

    result["days_remaining"] = (pd.to_datetime(result["expiry_date"]).dt.normalize() - reference_date).dt.days
    result["expected_sales_before_expiry"] = result["daily_demand"].fillna(0) * result["days_remaining"].clip(lower=0)
    result["unsold_units_estimate"] = (result["stock_available"] - result["expected_sales_before_expiry"]).clip(lower=0)
    result["estimated_unsold_stock_ratio"] = (result["unsold_units_estimate"] / result["stock_available"]).clip(upper=1)
    result.loc[insufficient, "estimated_unsold_stock_ratio"] = pd.NA
    result["cost_exposed"] = result["estimated_unsold_stock_ratio"] * result["stock_available"] * result["unit_cost"]
    result["recommendation"] = "Mantener precio y vigilar"
    result.loc[result["estimated_unsold_stock_ratio"] >= 0.30, "recommendation"] = "Aplicar acción preventiva"
    result.loc[result["estimated_unsold_stock_ratio"] >= 0.60, "recommendation"] = "Acelerar salida o redistribuir"
    result.loc[result["estimated_unsold_stock_ratio"] >= 0.85, "recommendation"] = "Liquidar o reasignar con prioridad"
    result.loc[
        (result["days_remaining"] <= 0) & result["estimated_unsold_stock_ratio"].notna(),
        "recommendation",
    ] = "Retirar o gestionar según la política de la empresa"
    return result, warnings
