"""Fetch current monthly Spanish food-retail volume context from Eurostat."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from src.data_pipeline import ROOT


SOURCE_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/sts_trtu_m"
    "?lang=en&freq=M&indic_bt=VOL_SLS&nace_r2=G47_FOOD&s_adj=CA&unit=I21&geo=ES&sinceTimePeriod=2024-01"
)
OUTPUT_PATH = ROOT / "data" / "external" / "eurostat_food_retail_volume_spain.json"


def parse_monthly_series(payload: dict[str, object]) -> list[dict[str, str | float]]:
    """Parse Eurostat's filtered JSON-stat response into ordered month/value rows."""
    dimensions = payload.get("dimension")
    values = payload.get("value")
    if not isinstance(dimensions, dict) or not isinstance(values, dict):
        raise ValueError("La respuesta de Eurostat no contiene dimensiones y valores.")

    time_dimension = dimensions.get("time")
    if not isinstance(time_dimension, dict):
        raise ValueError("La respuesta de Eurostat no contiene la dimensión temporal.")
    category = time_dimension.get("category")
    if not isinstance(category, dict):
        raise ValueError("La dimensión temporal no contiene categorías.")
    time_index = category.get("index")
    if not isinstance(time_index, dict):
        raise ValueError("La respuesta de Eurostat no contiene el índice temporal.")

    series: list[dict[str, str | float]] = []
    for month, position in sorted(time_index.items(), key=lambda item: item[1]):
        if not isinstance(month, str) or not isinstance(position, int):
            raise ValueError("Eurostat devolvió un periodo mensual con formato no válido.")
        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError as error:
            raise ValueError(f"Eurostat devolvió un periodo mensual no válido: {month}.") from error

        raw_value = values.get(str(position))
        if raw_value is None:
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Eurostat devolvió un índice no numérico para {month}.") from error
        if not math.isfinite(value):
            raise ValueError(f"Eurostat devolvió un índice no finito para {month}.")
        series.append({"month": month, "volume_index_2021_100": value})

    if not series:
        raise ValueError("Eurostat no devolvió observaciones mensuales para la consulta.")
    return series


def fetch_retail_volume_index(output_path: Path = OUTPUT_PATH) -> dict[str, object]:
    """Download and save the latest available monthly food-retail volume index."""
    with urlopen(SOURCE_URL, timeout=30) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("Eurostat devolvió una respuesta que no es un objeto JSON.")

    series = parse_monthly_series(payload)
    result: dict[str, object] = {
        "dataset": "sts_trtu_m",
        "indicator": "Retail volume of sales: food, beverages and tobacco",
        "country": "Spain",
        "frequency": "Monthly",
        "unit": "Index, 2021=100",
        "adjustment": "Calendar adjusted; not seasonally adjusted",
        "source": "Eurostat",
        "source_url": SOURCE_URL,
        "reuse_license": "CC BY 4.0",
        "attribution": "Eurostat (European Union)",
        "reuse_policy_url": "https://ec.europa.eu/eurostat/help/copyright-notice",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "latest_month": series[-1]["month"],
        "series": series,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(fetch_retail_volume_index(), ensure_ascii=False, indent=2))
