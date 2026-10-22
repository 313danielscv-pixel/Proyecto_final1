import pandas as pd

from src.lot_risk import MINIMUM_SALES_DAYS, build_lot_risk


def test_lot_risk_uses_uploaded_history_and_expiry() -> None:
    dates = pd.date_range("2026-01-01", periods=MINIMUM_SALES_DAYS, freq="D")
    sales = pd.DataFrame({"date": dates, "product_id": ["SKU-1"] * len(dates), "quantity": [2] * len(dates)})
    lots = pd.DataFrame(
        {
            "lot_id": ["LOT-1"],
            "product_id": ["SKU-1"],
            "stock_available": [20],
            "expiry_date": ["2026-02-03"],
            "unit_cost": [4.0],
        }
    )

    risks, warnings = build_lot_risk(lots, sales)

    assert not warnings
    assert risks.loc[0, "estimated_unsold_stock_ratio"] == 0.6
    assert risks.loc[0, "recommendation"] == "Acelerar salida o redistribuir"


def test_lot_risk_refuses_insufficient_history() -> None:
    sales = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=2), "product_id": ["SKU-1", "SKU-1"], "quantity": [1, 1]})
    lots = pd.DataFrame(
        {"lot_id": ["LOT-1"], "product_id": ["SKU-1"], "stock_available": [2], "expiry_date": ["2026-02-03"], "unit_cost": [1]}
    )

    risks, warnings = build_lot_risk(lots, sales)

    assert risks.empty
    assert warnings


def test_lot_risk_aggregates_multiple_transactions_per_day() -> None:
    dates = pd.date_range("2026-01-01", periods=MINIMUM_SALES_DAYS, freq="D")
    sales = pd.DataFrame(
        {
            "date": list(dates) + list(dates),
            "product_id": ["SKU-1"] * (2 * len(dates)),
            "quantity": [1] * (2 * len(dates)),
        }
    )
    lots = pd.DataFrame(
        {
            "lot_id": ["LOT-1"],
            "product_id": ["SKU-1"],
            "stock_available": [20],
            "expiry_date": ["2026-02-03"],
            "unit_cost": [4.0],
        }
    )

    risks, warnings = build_lot_risk(lots, sales)

    assert not warnings
    assert risks.loc[0, "daily_demand"] == 2
