import pytest

from src.fetch_eurostat_retail_context import parse_monthly_series


def test_parse_monthly_series_orders_by_eurostat_index_and_skips_missing_months() -> None:
    payload = {
        "dimension": {
            "time": {
                "category": {
                    "index": {"2024-02": 1, "2024-01": 0, "2024-03": 2}
                }
            }
        },
        "value": {"0": 98.2, "2": 103.5},
    }

    assert parse_monthly_series(payload) == [
        {"month": "2024-01", "volume_index_2021_100": 98.2},
        {"month": "2024-03", "volume_index_2021_100": 103.5},
    ]


def test_parse_monthly_series_rejects_empty_response() -> None:
    payload = {
        "dimension": {"time": {"category": {"index": {"2024-01": 0}}}},
        "value": {},
    }

    with pytest.raises(ValueError, match="no devolvió observaciones"):
        parse_monthly_series(payload)
