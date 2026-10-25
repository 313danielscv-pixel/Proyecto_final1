"""Reusable profiling, statistical analysis, uncertainty and drift helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class AnalysisWarning:
    """A limitation that prevents over-interpreting an EDA result."""

    message: str


def profile_data(data: pd.DataFrame) -> pd.DataFrame:
    """Return a compact profile for every source column."""
    rows: list[dict[str, object]] = []
    for column in data.columns:
        series = data[column]
        rows.append(
            {
                "columna": column,
                "tipo": str(series.dtype),
                "filas_nulas": int(series.isna().sum()),
                "porcentaje_nulo": float(series.isna().mean()),
                "valores_unicos": int(series.nunique(dropna=True)),
                "ejemplo": str(series.dropna().iloc[0]) if series.notna().any() else "",
            }
        )
    return pd.DataFrame(rows)


def quality_summary(data: pd.DataFrame) -> dict[str, object]:
    """Measure generic quality risks without applying unverified business rules."""
    numeric = data.select_dtypes(include="number")
    negative_counts = {column: int((numeric[column] < 0).sum()) for column in numeric.columns}
    impossible = {column: count for column, count in negative_counts.items() if count}
    return {
        "rows": len(data),
        "columns": len(data.columns),
        "duplicate_rows": int(data.duplicated().sum()),
        "missing_cells": int(data.isna().sum().sum()),
        "negative_values": impossible,
        "potential_leakage_columns": [
            column
            for column in data.columns
            if any(token in column.lower() for token in ("target", "label", "outcome", "resultado", "realizado"))
        ],
    }


def numeric_summary(data: pd.DataFrame, column: str) -> pd.DataFrame:
    """Return descriptive statistics and IQR outlier count for one numeric variable."""
    values = pd.to_numeric(data[column], errors="coerce").dropna()
    if values.empty:
        return pd.DataFrame()
    first_quartile, third_quartile = values.quantile([0.25, 0.75])
    interquartile_range = third_quartile - first_quartile
    outliers = ((values < first_quartile - 1.5 * interquartile_range) | (values > third_quartile + 1.5 * interquartile_range)).sum()
    return pd.DataFrame(
        [
            {
                "media": values.mean(),
                "mediana": values.median(),
                "desviacion_estandar": values.std(),
                "minimo": values.min(),
                "percentil_25": first_quartile,
                "percentil_75": third_quartile,
                "maximo": values.max(),
                "asimetria": values.skew(),
                "atipicos_iqr": int(outliers),
                "muestra": len(values),
            }
        ]
    )


def bootstrap_mean_interval(values: pd.Series, iterations: int = 500, confidence: float = 0.95) -> tuple[float, float, float]:
    """Estimate a non-parametric confidence interval for independent observations."""
    clean = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
    if len(clean) < 10:
        raise ValueError("Se necesitan al menos 10 observaciones para estimar un intervalo bootstrap.")
    generator = np.random.default_rng(42)
    means = np.array([generator.choice(clean, size=len(clean), replace=True).mean() for _ in range(iterations)])
    alpha = (1 - confidence) / 2
    return float(clean.mean()), float(np.quantile(means, alpha)), float(np.quantile(means, 1 - alpha))


def temporal_summary(data: pd.DataFrame, date_column: str, value_column: str) -> tuple[pd.DataFrame, list[AnalysisWarning]]:
    """Aggregate a daily series and flag z-score anomalies where enough dates exist."""
    frame = data[[date_column, value_column]].copy()
    frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
    frame[value_column] = pd.to_numeric(frame[value_column], errors="coerce")
    frame = frame.dropna()
    frame[date_column] = frame[date_column].dt.normalize()
    frame = frame.groupby(date_column, as_index=False)[value_column].sum().sort_values(date_column)
    warnings: list[AnalysisWarning] = []
    if len(frame) < 14:
        warnings.append(AnalysisWarning("Menos de 14 periodos: no se evalúan estacionalidad ni anomalías temporales."))
        frame["anomaly"] = False
        return frame, warnings
    standard_deviation = frame[value_column].std()
    if standard_deviation == 0:
        warnings.append(AnalysisWarning("La serie no varía: no se pueden identificar anomalías por desviación estándar."))
        frame["anomaly"] = False
        return frame, warnings
    frame["z_score"] = (frame[value_column] - frame[value_column].mean()) / standard_deviation
    frame["anomaly"] = frame["z_score"].abs() >= 3
    return frame, warnings


def population_stability_index(reference: pd.Series, current: pd.Series, bins: int = 10) -> float:
    """Measure distribution drift with a PSI score; values need enough numeric observations."""
    baseline = pd.to_numeric(reference, errors="coerce").dropna()
    observed = pd.to_numeric(current, errors="coerce").dropna()
    if len(baseline) < 20 or len(observed) < 20:
        raise ValueError("Se necesitan al menos 20 observaciones en cada periodo para calcular deriva.")
    edges = np.unique(np.quantile(baseline, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        raise ValueError("La variable no tiene variación suficiente para calcular deriva.")
    edges[0] = -np.inf
    edges[-1] = np.inf
    expected_counts, _ = np.histogram(baseline, bins=edges)
    actual_counts, _ = np.histogram(observed, bins=edges)
    expected = np.clip(expected_counts / len(baseline), 1e-6, None)
    actual = np.clip(actual_counts / len(observed), 1e-6, None)
    return float(np.sum((actual - expected) * np.log(actual / expected)))


def segment_rows(data: pd.DataFrame, columns: list[str], clusters: int) -> pd.Series:
    """Cluster complete numeric rows only when the sample supports the requested clusters."""
    values = data[columns].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(values) < clusters * 5:
        raise ValueError("La muestra es demasiado pequeña para el número de segmentos solicitado.")
    scaled = StandardScaler().fit_transform(values)
    labels = KMeans(n_clusters=clusters, n_init=10, random_state=42).fit_predict(scaled)
    result = pd.Series(pd.NA, index=data.index, dtype="Int64")
    result.loc[values.index] = labels
    return result
