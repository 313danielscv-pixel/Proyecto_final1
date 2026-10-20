"""Fetch the official Eurostat food-waste indicator used as project context."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.request import urlopen

from src.data_pipeline import ROOT


URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
    "cei_pc035?lang=EN&geo=ES&time=2022"
)
OUTPUT = ROOT / "data" / "external" / "eurostat_food_waste_spain_2022.json"


def fetch_context(output_path: Path = OUTPUT) -> dict[str, object]:
    """Download and save the official country-level contextual indicator."""
    with urlopen(URL, timeout=30) as response:
        payload = json.load(response)
    value = payload.get("value", {}).get("0")
    if value is None:
        raise ValueError("Eurostat response did not contain the expected Spain 2022 observation.")
    result = {
        "indicator": "Food waste collected per capita",
        "country": "Spain",
        "year": 2022,
        "value_kg_per_capita": value,
        "dataset": "cei_pc035",
        "source_url": URL,
        "source": "Eurostat",
        "methodological_note": payload["extension"]["description"],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(fetch_context(), ensure_ascii=False, indent=2))
