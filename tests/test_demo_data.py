from pathlib import Path

import pandas as pd

from src.demo_data import build_demo_bundle
from src.lot_risk import build_lot_risk


def _synthetic_training_data() -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=35, freq="D")
    return pd.DataFrame(
        [
            {
                "store_id": 1,
                "product_id": product_id,
                "dt": date,
                "sale_amount": product_id + date.dayofweek,
                "discount": 1.0,
                "holiday_flag": 0,
            }
            for product_id in range(1, 9)
            for date in dates
        ]
    )


def test_demo_bundle_contains_real_and_scenario_files_without_reading_parquet(monkeypatch, tmp_path) -> None:
    def fail_read_parquet(*_args, **_kwargs):
        raise AssertionError("La prueba de la demo no debe depender de Parquet.")

    monkeypatch.setattr(pd, "read_parquet", fail_read_parquet)
    paths = build_demo_bundle(train_data=_synthetic_training_data(), output_directory=tmp_path)

    assert set(paths) == {"sales", "inventory", "costs", "lots"}
    assert all(Path(path).exists() for path in paths.values())
    assert (tmp_path / "README_DEMO.json").exists()
    sales = pd.read_csv(paths["sales"])
    lots = pd.read_csv(paths["lots"])

    risks, warnings = build_lot_risk(lots, sales, assume_complete_period=True)

    assert not warnings
    assert risks["estimated_unsold_stock_ratio"].nunique() >= 4
    assert risks["recommendation"].nunique() >= 3
