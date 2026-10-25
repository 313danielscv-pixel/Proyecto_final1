from __future__ import annotations

import pandas as pd
import pytest

from src.advanced_eda import (
    bootstrap_mean_interval,
    numeric_summary,
    population_stability_index,
    profile_data,
    quality_summary,
    segment_rows,
    temporal_summary,
)


def test_profile_and_quality_report_missing_duplicates_and_negatives() -> None:
    data = pd.DataFrame(
        {"value": [1, -2, None, 1], "category": ["a", "b", "c", "a"], "target_result": [0, 1, 1, 0]}
    )

    profile = profile_data(data)
    quality = quality_summary(data)

    assert profile.loc[profile["columna"] == "value", "filas_nulas"].item() == 1
    assert quality["duplicate_rows"] == 1
    assert quality["negative_values"] == {"value": 1}
    assert quality["potential_leakage_columns"] == ["target_result"]


def test_numeric_summary_detects_iqr_outlier() -> None:
    summary = numeric_summary(pd.DataFrame({"value": [1, 2, 2, 3, 100]}), "value")

    assert summary["atipicos_iqr"].item() == 1


def test_bootstrap_requires_minimum_sample_and_returns_interval() -> None:
    with pytest.raises(ValueError, match="al menos 10"):
        bootstrap_mean_interval(pd.Series(range(9)))

    mean, lower, upper = bootstrap_mean_interval(pd.Series(range(20)))
    assert lower < mean < upper


def test_temporal_anomaly_analysis() -> None:
    series = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=20),
            "value": [10] * 19 + [100],
        }
    )
    result, warnings = temporal_summary(series, "date", "value")
    assert not warnings
    assert result["anomaly"].iloc[-1]


def test_temporal_summary_combines_timestamps_within_the_same_day() -> None:
    series = pd.DataFrame(
        {
            "date": ["2024-01-01 09:00", "2024-01-01 16:00", "2024-01-02 09:00"],
            "value": [2, 3, 4],
        }
    )

    result, _ = temporal_summary(series, "date", "value")

    assert result["value"].tolist() == [5, 4]


def test_drift_and_clustering_enforce_valid_samples() -> None:
    with pytest.raises(ValueError, match="al menos 20"):
        population_stability_index(pd.Series(range(5)), pd.Series(range(5)))

    data = pd.DataFrame({"x": list(range(20)), "y": list(range(20, 40))})
    labels = segment_rows(data, ["x", "y"], 2)
    assert labels.notna().all()


def test_drift_counts_values_outside_reference_range_and_clustering_ignores_infinities() -> None:
    reference = pd.Series(range(20))
    current = pd.Series([100] * 20)
    assert population_stability_index(reference, current) > 1

    data = pd.DataFrame({"x": list(range(20)) + [float("inf")], "y": list(range(20, 40)) + [1]})
    labels = segment_rows(data, ["x", "y"], 2)
    assert labels.iloc[:-1].notna().all()
    assert pd.isna(labels.iloc[-1])
