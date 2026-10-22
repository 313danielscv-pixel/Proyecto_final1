"""Explainable lot-risk calculations driven by a company's uploaded history."""

from __future__ import annotations

import pandas as pd

from src.business_intelligence import average_daily_demand


MINIMUM_HISTORY_DAYS = 30


def build_lot_risk(
    lots: pd.DataFrame,
    sales: pd.DataFrame,
    assume_complete_period: bool = False,
) -> tuple[pd.DataFrame, list[str]]:
    """Estimate lot risk using calendar demand within a confirmed complete sales period."""
    if not assume_complete_period:
        return pd.DataFrame(), [
            "Confirma que las ventas cubren todos los días del periodo antes de estimar riesgo por lote."
        ]

    sales = sales.loc[:, ["date", "product_id", "quantity"]].copy()
    sales["date"] = pd.to_datetime(sales["date"], errors="coerce").dt.normalize()
    sales["quantity"] = pd.to_numeric(sales["quantity"], errors="coerce")
    sales = sales.dropna(subset=["date", "product_id", "quantity"])
    sales = sales.loc[sales["quantity"].ge(0)]
    daily_sales = sales.groupby(["product_id", "date"], as_index=False)["quantity"].sum()
    sales_days = daily_sales.groupby("product_id")["date"].nunique()
    product_starts = daily_sales.groupby("product_id")["date"].min()
    extract_end = daily_sales["date"].max()
    history_days = (extract_end - product_starts).dt.days + 1
    if history_days.empty or history_days.max() < MINIMUM_HISTORY_DAYS:
        return pd.DataFrame(), [
            f"Se necesitan al menos {MINIMUM_HISTORY_DAYS} días naturales de historial por producto para calcular riesgo por lote."
        ]

    reference_date = extract_end
    daily_demand = average_daily_demand(
        sales,
        assume_complete_period=True,
    ).rename(columns={"quantity": "daily_demand"})
    result = lots.merge(daily_demand, on="product_id", how="left")
    result["sales_days"] = result["product_id"].map(sales_days).fillna(0).astype(int)
    result["history_days"] = result["product_id"].map(history_days).fillna(0).astype(int)
    warnings: list[str] = []
    insufficient = result["history_days"] < MINIMUM_HISTORY_DAYS
    if insufficient.any():
        products = ", ".join(result.loc[insufficient, "product_id"].astype(str).unique()[:5])
        warnings.append(f"Sin historial suficiente para: {products}. Esos lotes no reciben una estimación.")

    result["days_remaining"] = (pd.to_datetime(result["expiry_date"]).dt.normalize() - reference_date).dt.days
    result["expected_sales_before_expiry"] = result["daily_demand"].fillna(0) * result["days_remaining"].clip(lower=0)
    result["unsold_units_estimate"] = (result["stock_available"] - result["expected_sales_before_expiry"]).clip(lower=0)
    result["estimated_unsold_stock_ratio"] = (result["unsold_units_estimate"] / result["stock_available"]).clip(upper=1)
    result.loc[insufficient, "estimated_unsold_stock_ratio"] = pd.NA
    result["cost_exposed"] = result["estimated_unsold_stock_ratio"] * result["stock_available"] * result["unit_cost"]
    decision_ratio = (result["estimated_unsold_stock_ratio"] * 100).round(1) / 100
    result["risk_level"] = pd.cut(
        decision_ratio,
        bins=[0.0, 0.30, 0.60, 0.85, 1.000001],
        labels=["Bajo", "Medio", "Alto", "Crítico"],
        right=False,
    )
    result["recommendation"] = "Mantener precio y vigilar"
    result.loc[result["risk_level"].eq("Medio"), "recommendation"] = "Aplicar acción preventiva"
    result.loc[result["risk_level"].eq("Alto"), "recommendation"] = "Acelerar salida o redistribuir"
    result.loc[result["risk_level"].eq("Crítico"), "recommendation"] = "Liquidar o reasignar con prioridad"
    result.loc[
        (result["days_remaining"] <= 0) & result["estimated_unsold_stock_ratio"].notna(),
        "recommendation",
    ] = "Retirar o gestionar según la política de la empresa"
    return result, warnings
