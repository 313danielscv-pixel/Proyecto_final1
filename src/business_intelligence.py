"""Reusable demand, inventory, profitability and scenario calculations."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ScenarioResult:
    """A transparent economic scenario; values are estimates, never realised savings."""

    revenue: float
    product_cost: float
    holding_cost: float
    gross_margin: float
    margin_change: float


def average_daily_demand(sales: pd.DataFrame) -> pd.DataFrame:
    """Average units per observed product-day after combining same-day transactions.

    Dates without a transaction remain unknown rather than being imputed as zero because
    uploaded extracts may omit days outside their reporting window.
    """
    required = {"date", "product_id", "quantity"}
    missing = required - set(sales.columns)
    if missing:
        raise ValueError(f"Faltan columnas para calcular demanda diaria: {', '.join(sorted(missing))}.")
    daily_sales = sales.loc[:, ["date", "product_id", "quantity"]].copy()
    daily_sales["date"] = pd.to_datetime(daily_sales["date"], errors="coerce").dt.normalize()
    daily_sales["quantity"] = pd.to_numeric(daily_sales["quantity"], errors="coerce")
    daily_sales = daily_sales.dropna(subset=["date", "product_id", "quantity"])
    daily_sales = daily_sales.groupby(["product_id", "date"], as_index=False)["quantity"].sum()
    return daily_sales.groupby("product_id", as_index=False)["quantity"].mean()


def sales_eda(sales: pd.DataFrame) -> dict[str, pd.DataFrame | dict[str, int | float]]:
    """Build transparent sales summaries without imputing unobserved dates as zero."""
    required = {"date", "product_id", "quantity"}
    missing = required - set(sales.columns)
    if missing:
        raise ValueError(f"Faltan columnas para analizar ventas: {', '.join(sorted(missing))}.")
    sales = sales.reset_index(drop=True)

    dates = pd.to_datetime(sales["date"], errors="coerce").dt.normalize()
    products = sales["product_id"].astype("string").str.strip()
    quantities = pd.to_numeric(sales["quantity"], errors="coerce")
    invalid_dates = dates.isna()
    invalid_products = products.isna() | products.fillna("").eq("")
    invalid_quantities = (
        quantities.isna()
        | quantities.lt(0)
        | quantities.isin([float("inf"), float("-inf")])
    )
    valid_rows = ~(invalid_dates | invalid_products | invalid_quantities)
    clean_sales = pd.DataFrame(
        {"date": dates, "product_id": products, "quantity": quantities},
        index=sales.index,
    ).loc[valid_rows].copy()

    daily_observed = (
        clean_sales.groupby("date", as_index=False)["quantity"]
        .sum()
        .sort_values("date")
    )
    if daily_observed.empty:
        daily = pd.DataFrame(
            columns=["date", "quantity", "has_observation", "average_7d", "average_30d", "outlier_iqr"]
        )
    else:
        calendar = pd.date_range(
            daily_observed["date"].min(),
            daily_observed["date"].max(),
            freq="D",
            name="date",
        )
        daily = daily_observed.set_index("date").reindex(calendar)
        daily.index.name = "date"
        daily["has_observation"] = daily["quantity"].notna()
        daily["average_7d"] = daily["quantity"].rolling(7, min_periods=1).mean()
        daily["average_30d"] = daily["quantity"].rolling(30, min_periods=1).mean()
        daily["outlier_iqr"] = False
        observed_values = daily["quantity"].dropna()
        first_quartile, third_quartile = observed_values.quantile([0.25, 0.75])
        interquartile_range = third_quartile - first_quartile
        if len(observed_values) >= 14 and interquartile_range > 0:
            lower_bound = first_quartile - 1.5 * interquartile_range
            upper_bound = third_quartile + 1.5 * interquartile_range
            daily["outlier_iqr"] = (
                daily["quantity"].lt(lower_bound) | daily["quantity"].gt(upper_bound)
            ).fillna(False)
        daily = daily.reset_index()

    products_summary = (
        clean_sales.groupby("product_id", as_index=False)
        .agg(
            quantity=("quantity", "sum"),
            records=("quantity", "size"),
            sale_days=("date", "nunique"),
        )
        .sort_values(["quantity", "product_id"], ascending=[False, True])
    )
    total_units = products_summary["quantity"].sum()
    products_summary["share_pct"] = (
        products_summary["quantity"] / total_units * 100
        if total_units > 0
        else float("nan")
    )

    observed_daily = daily_observed.copy()
    if observed_daily.empty:
        weekday_summary = pd.DataFrame(
            columns=["weekday", "weekday_index", "quantity", "average_per_observed_day", "observed_days"]
        )
        weekly_summary = pd.DataFrame(
            columns=["week_start", "quantity", "observed_days", "max_daily_units"]
        )
    else:
        observed_daily["weekday_index"] = observed_daily["date"].dt.dayofweek
        weekday_names = {
            0: "Lunes",
            1: "Martes",
            2: "Miércoles",
            3: "Jueves",
            4: "Viernes",
            5: "Sábado",
            6: "Domingo",
        }
        weekday_summary = (
            observed_daily.groupby("weekday_index", as_index=False)
            .agg(
                quantity=("quantity", "sum"),
                average_per_observed_day=("quantity", "mean"),
                observed_days=("date", "size"),
            )
            .sort_values("weekday_index")
        )
        weekday_summary["weekday"] = weekday_summary["weekday_index"].map(weekday_names)
        observed_daily["week_start"] = observed_daily["date"] - pd.to_timedelta(
            observed_daily["date"].dt.dayofweek,
            unit="D",
        )
        weekly_summary = (
            observed_daily.groupby("week_start", as_index=False)
            .agg(
                quantity=("quantity", "sum"),
                observed_days=("date", "size"),
                max_daily_units=("quantity", "max"),
            )
            .sort_values("week_start")
        )

    result: dict[str, pd.DataFrame | dict[str, int | float]] = {
        "daily_demand": daily,
        "products": products_summary,
        "weekday_demand": weekday_summary,
        "weekly_demand": weekly_summary,
    }
    if "unit_price" in sales:
        prices = pd.to_numeric(sales["unit_price"], errors="coerce")
        revenue = clean_sales.assign(unit_price=prices.loc[clean_sales.index])
        revenue = revenue.dropna(subset=["unit_price"])
        revenue = revenue.loc[
            revenue["unit_price"].ge(0) & ~revenue["unit_price"].isin([float("inf"), float("-inf")])
        ]
        result["revenue_by_product"] = (
            revenue.assign(revenue=revenue["quantity"] * revenue["unit_price"])
            .groupby("product_id", as_index=False)["revenue"]
            .sum()
            .sort_values("revenue", ascending=False)
        )

    if daily_observed.empty:
        calendar_days = observed_days = 0
    else:
        calendar_days = int((daily_observed["date"].max() - daily_observed["date"].min()).days + 1)
        observed_days = int(len(daily_observed))
    result["quality"] = {
        "total_rows": int(len(sales)),
        "valid_rows": int(valid_rows.sum()),
        "invalid_dates": int(invalid_dates.sum()),
        "missing_products": int(invalid_products.sum()),
        "invalid_quantities": int(invalid_quantities.sum()),
        "duplicate_rows": int(sales.duplicated().sum()),
        "missing_cells": int(sales.isna().sum().sum()),
        "observed_days": observed_days,
        "calendar_days": calendar_days,
        "missing_days": calendar_days - observed_days,
        "coverage_pct": observed_days / calendar_days * 100 if calendar_days else 0.0,
        "zero_sales_days": int(daily_observed["quantity"].eq(0).sum()) if observed_days else 0,
    }
    return result


def attach_cost_reference(inventory: pd.DataFrame, costs: pd.DataFrame | None) -> pd.DataFrame:
    """Fill missing inventory prices and costs from the product cost reference."""
    result = inventory.copy()
    if costs is None or "product_id" not in result or "product_id" not in costs:
        return result
    cost_columns = [column for column in ("product_id", "unit_cost", "unit_price") if column in costs]
    if len(cost_columns) == 1:
        return result
    cost_reference = costs[cost_columns].drop_duplicates("product_id")
    result = result.merge(cost_reference, on="product_id", how="left", suffixes=("", "_costs"))
    for column in ("unit_cost", "unit_price"):
        cost_column = f"{column}_costs"
        if cost_column not in result:
            continue
        if column in result:
            result[column] = result[column].fillna(result[cost_column])
        else:
            result[column] = result[cost_column]
        result = result.drop(columns=cost_column)
    return result


def inventory_intelligence(inventory: pd.DataFrame, daily_demand: pd.DataFrame) -> pd.DataFrame:
    """Calculate coverage and stock risks from observed stock and average daily demand."""
    demand = daily_demand.rename(columns={"quantity": "daily_demand"})
    result = inventory.merge(demand, on="product_id", how="left")
    result["daily_demand"] = result["daily_demand"].fillna(0)
    result["coverage_days"] = result["on_hand_units"] / result["daily_demand"].replace(0, pd.NA)
    result["capital_exposed"] = result["on_hand_units"] * result.get("unit_cost", 0)
    if "unit_price" in result and "unit_cost" in result:
        result["unit_margin"] = result["unit_price"] - result["unit_cost"]
    lead_time = result.get("reorder_lead_days", pd.Series(0, index=result.index)).fillna(0)
    minimum_stock = result.get("minimum_stock", pd.Series(0, index=result.index)).fillna(0)
    result["risk"] = "equilibrado"
    result.loc[(result["coverage_days"].fillna(float("inf")) < lead_time) | (result["on_hand_units"] < minimum_stock), "risk"] = "rotura"
    result.loc[result["coverage_days"].fillna(0) > 45, "risk"] = "sobrestock"
    return result


def compare_scenario(
    baseline_units: float,
    baseline_price: float,
    unit_cost: float,
    holding_cost_per_unit_day: float,
    days_held: float,
    price_change_pct: float,
    demand_change_pct: float,
) -> ScenarioResult:
    """Compare a price and demand assumption with the current operating baseline."""
    scenario_units = baseline_units * (1 + demand_change_pct / 100)
    scenario_price = baseline_price * (1 + price_change_pct / 100)
    revenue = scenario_units * scenario_price
    product_cost = scenario_units * unit_cost
    holding_cost = scenario_units * holding_cost_per_unit_day * days_held
    gross_margin = revenue - product_cost - holding_cost
    baseline_margin = baseline_units * baseline_price - baseline_units * unit_cost - (
        baseline_units * holding_cost_per_unit_day * days_held
    )
    return ScenarioResult(revenue, product_cost, holding_cost, gross_margin, gross_margin - baseline_margin)


def scenario_sensitivity(
    baseline_units: float,
    baseline_price: float,
    unit_cost: float,
    holding_cost_per_unit_day: float,
    days_held: float,
    price_changes: tuple[int, ...] = (-20, -10, 0, 10, 20),
    demand_changes: tuple[int, ...] = (-20, -10, 0, 10, 20),
) -> pd.DataFrame:
    """Compare estimated margin changes across explicit price and demand assumptions."""
    rows = [
        {
            "price_change_pct": price_change,
            "demand_change_pct": demand_change,
            "margin_change": compare_scenario(
                baseline_units,
                baseline_price,
                unit_cost,
                holding_cost_per_unit_day,
                days_held,
                price_change,
                demand_change,
            ).margin_change,
        }
        for demand_change in demand_changes
        for price_change in price_changes
    ]
    return pd.DataFrame(rows)
