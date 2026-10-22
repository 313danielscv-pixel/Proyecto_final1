import pandas as pd

from src.lot_risk import MINIMUM_HISTORY_DAYS, build_lot_risk


def test_lot_risk_uses_uploaded_history_and_expiry() -> None:
    dates = pd.date_range("2026-01-01", periods=MINIMUM_HISTORY_DAYS, freq="D")
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

    risks, warnings = build_lot_risk(lots, sales, assume_complete_period=True)

    assert not warnings
    assert risks.loc[0, "estimated_unsold_stock_ratio"] == 0.6
    assert risks.loc[0, "recommendation"] == "Acelerar salida o redistribuir"


def test_lot_risk_refuses_insufficient_history() -> None:
    sales = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=2), "product_id": ["SKU-1", "SKU-1"], "quantity": [1, 1]})
    lots = pd.DataFrame(
        {"lot_id": ["LOT-1"], "product_id": ["SKU-1"], "stock_available": [2], "expiry_date": ["2026-02-03"], "unit_cost": [1]}
    )

    risks, warnings = build_lot_risk(lots, sales, assume_complete_period=True)

    assert risks.empty
    assert warnings


def test_lot_risk_aggregates_multiple_transactions_per_day() -> None:
    dates = pd.date_range("2026-01-01", periods=MINIMUM_HISTORY_DAYS, freq="D")
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

    risks, warnings = build_lot_risk(lots, sales, assume_complete_period=True)

    assert not warnings
    assert risks.loc[0, "daily_demand"] == 2


def test_lot_risk_uses_calendar_days_for_sparse_sales() -> None:
    sales = pd.DataFrame(
        {
            "date": [
                "2026-01-01",
                "2026-01-06",
                "2026-01-11",
                "2026-01-16",
                "2026-01-21",
                "2026-01-26",
                "2026-01-30",
            ],
            "product_id": ["SKU-1"] * 6 + ["SKU-2"],
            "quantity": [10, 10, 10, 10, 10, 10, 1],
        }
    )
    lots = pd.DataFrame(
        {
            "lot_id": ["LOT-1"],
            "product_id": ["SKU-1"],
            "stock_available": [40],
            "expiry_date": ["2026-02-03"],
            "unit_cost": [4.0],
        }
    )

    risks, warnings = build_lot_risk(lots, sales, assume_complete_period=True)

    assert not warnings
    assert risks.loc[0, "sales_days"] == 6
    assert risks.loc[0, "history_days"] == 30
    assert risks.loc[0, "daily_demand"] == 2
    assert risks.loc[0, "estimated_unsold_stock_ratio"] == 0.8


def test_lot_recommendations_match_the_displayed_risk_band() -> None:
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    sales = pd.DataFrame(
        [
            {"date": date, "product_id": product_id, "quantity": 1}
            for product_id in ("SKU-1", "SKU-2")
            for date in dates
        ]
    )
    lots = pd.DataFrame(
        {
            "lot_id": ["LOT-1", "LOT-2"],
            "product_id": ["SKU-1", "SKU-2"],
            "stock_available": [4 / (1 - 0.5996), 4 / (1 - 0.6004)],
            "expiry_date": ["2026-02-03", "2026-02-03"],
            "unit_cost": [4.0, 4.0],
        }
    )

    risks, warnings = build_lot_risk(lots, sales, assume_complete_period=True)

    assert not warnings
    assert risks["estimated_unsold_stock_ratio"].map(lambda ratio: f"{ratio:.1%}").tolist() == [
        "60.0%",
        "60.0%",
    ]
    assert risks["recommendation"].nunique() == 1
    assert risks["recommendation"].iloc[0] == "Acelerar salida o redistribuir"
    assert risks["risk_level"].nunique() == 1
    assert risks["risk_level"].iloc[0] == "Alto"


def test_lot_risk_requires_complete_sales_period_confirmation() -> None:
    sales = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=MINIMUM_HISTORY_DAYS, freq="D"),
            "product_id": ["SKU-1"] * MINIMUM_HISTORY_DAYS,
            "quantity": [2] * MINIMUM_HISTORY_DAYS,
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

    assert risks.empty
    assert "Confirma que las ventas cubren" in warnings[0]
