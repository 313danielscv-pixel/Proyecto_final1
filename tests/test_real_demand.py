import pandas as pd

from src.real_demand import evaluate_demand_models


def test_moving_average_is_compared_with_seasonal_naive_on_held_out_days() -> None:
    train = pd.DataFrame(
        {
            "store_id": [1] * 14,
            "product_id": [100] * 14,
            "dt": pd.date_range("2026-01-01", periods=14, freq="D"),
            "sale_amount": range(1, 15),
        }
    )
    evaluation = pd.DataFrame(
        {
            "store_id": [1] * 7,
            "product_id": [100] * 7,
            "dt": pd.date_range("2026-01-15", periods=7, freq="D"),
            "sale_amount": [10] * 7,
        }
    )

    forecasts, metrics = evaluate_demand_models(train, evaluation, max_series=1)

    assert len(forecasts) == 7
    assert forecasts["forecast_units"].tolist() == [8, 9, 10, 11, 12, 13, 14]
    assert forecasts["moving_average_7d_units"].tolist() == [11] * 7
    assert metrics["models"]["moving_average_7d"]["mae"] == 1
    assert metrics["models"]["seasonal_naive"]["mae"] > 1
    assert metrics["best_model_by_mae"] == "moving_average_7d"
