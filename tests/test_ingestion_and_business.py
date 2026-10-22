import pandas as pd

from src.business_intelligence import (
    average_daily_demand,
    attach_cost_reference,
    compare_scenario,
    inventory_intelligence,
    sales_eda,
    scenario_sensitivity,
)
from src.contracts import INVENTORY_CONTRACT, SALES_CONTRACT
from src.ingestion import parse_csv, parse_free_tabular


def test_sales_aliases_are_mapped_and_parsed() -> None:
    data, report = parse_csv(b"fecha,sku,unidades\n2026-01-01,SKU-1,4\n", SALES_CONTRACT)

    assert set(data.columns) == {"date", "product_id", "quantity"}
    assert report.missing_required == ()
    assert report.valid_rows == 1


def test_invalid_numeric_values_are_reported() -> None:
    _, report = parse_csv(b"fecha,sku,unidades\n2026-01-01,SKU-1,-4\n", SALES_CONTRACT)

    assert report.invalid_values["quantity"] == 1
    assert report.valid_rows == 0


def test_free_eda_upload_preserves_uncontracted_columns() -> None:
    data = parse_free_tabular(
        b"fecha,beneficio,temperatura,comentario\n2026-01-01,12.5,4.2,correcto\n",
        "analisis.csv",
    )

    assert data.columns.tolist() == ["fecha", "beneficio", "temperatura", "comentario"]


def test_daily_demand_combines_transactions_from_the_same_product_day() -> None:
    sales = pd.DataFrame(
        {
            "date": ["2026-01-01 09:00", "2026-01-01 16:00", "2026-01-02"],
            "product_id": ["SKU-1", "SKU-1", "SKU-1"],
            "quantity": [2, 4, 6],
        }
    )

    demand = average_daily_demand(sales)

    assert demand.loc[0, "quantity"] == 6


def test_sales_eda_preserves_missing_days_and_reports_invalid_rows() -> None:
    sales = pd.DataFrame(
        {
            "date": [
                "2026-01-01",
                "2026-01-01",
                "2026-01-03",
                "fecha no válida",
                "2026-01-02",
                "2026-01-03",
            ],
            "product_id": ["SKU-1", "SKU-2", "SKU-1", "SKU-1", "", "SKU-2"],
            "quantity": [2, 3, 0, 4, 3, -1],
        }
    )

    result = sales_eda(sales)
    daily = result["daily_demand"]
    products = result["products"]
    quality = result["quality"]

    assert isinstance(daily, pd.DataFrame)
    assert isinstance(products, pd.DataFrame)
    assert isinstance(quality, dict)
    assert daily["quantity"].iloc[0] == 5
    assert pd.isna(daily["quantity"].iloc[1])
    assert daily["quantity"].iloc[2] == 0
    assert daily["average_7d"].iloc[2] == 2.5
    assert products.loc[products["product_id"].eq("SKU-2"), "share_pct"].item() == 60
    assert quality["valid_rows"] == 3
    assert quality["invalid_dates"] == 1
    assert quality["missing_products"] == 1
    assert quality["invalid_quantities"] == 1
    assert quality["observed_days"] == 2
    assert quality["calendar_days"] == 3
    assert quality["missing_days"] == 1
    assert quality["zero_sales_days"] == 1


def test_inventory_risk_uses_observed_stock_and_demand() -> None:
    inventory = pd.DataFrame(
        {"product_id": ["SKU-1", "SKU-2"], "on_hand_units": [4, 500], "reorder_lead_days": [5, 2]}
    )
    demand = pd.DataFrame({"product_id": ["SKU-1", "SKU-2"], "quantity": [2.0, 5.0]})

    result = inventory_intelligence(inventory, demand)

    assert result.loc[0, "risk"] == "rotura"
    assert result.loc[1, "risk"] == "sobrestock"


def test_cost_reference_fills_missing_inventory_cost_without_overwriting_values() -> None:
    inventory = pd.DataFrame(
        {"product_id": ["SKU-1", "SKU-2"], "on_hand_units": [4, 8], "unit_cost": [2.0, None]}
    )
    costs = pd.DataFrame(
        {"product_id": ["SKU-1", "SKU-2"], "unit_cost": [3.0, 5.0], "unit_price": [7.0, 9.0]}
    )

    result = attach_cost_reference(inventory, costs)

    assert result["unit_cost"].tolist() == [2.0, 5.0]
    assert result["unit_price"].tolist() == [7.0, 9.0]


def test_scenario_result_distinguishes_estimated_margin_change() -> None:
    scenario = compare_scenario(10, 10, 4, 0.1, 2, -10, 20)

    assert scenario.revenue == 108
    assert round(scenario.margin_change, 2) == -0.40


def test_scenario_sensitivity_includes_baseline_and_all_assumption_pairs() -> None:
    result = scenario_sensitivity(10, 10, 4, 0.1, 2)

    baseline = result.loc[
        result["price_change_pct"].eq(0) & result["demand_change_pct"].eq(0),
        "margin_change",
    ]
    assert len(result) == 25
    assert baseline.iloc[0] == 0
