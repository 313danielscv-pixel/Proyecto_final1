"""CSV mapping and quality checks for company data uploads."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import pandas as pd

from src.contracts import BusinessModule, DatasetContract, ValueType


@dataclass(frozen=True)
class QualityReport:
    """Summarise mapping and row-level quality without changing the source upload."""

    mapped_columns: dict[str, str]
    missing_required: tuple[str, ...]
    invalid_values: dict[str, int]
    duplicate_rows: int
    valid_rows: int
    total_rows: int


def _normalise(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def infer_mapping(columns: list[str], contract: DatasetContract) -> dict[str, str]:
    """Match canonical fields to an uploaded header using documented aliases."""
    normalized = {_normalise(column): column for column in columns}
    mapping: dict[str, str] = {}
    for field in contract.columns:
        candidates = (field.name, *field.aliases)
        source = next((normalized[_normalise(item)] for item in candidates if _normalise(item) in normalized), None)
        if source is not None:
            mapping[field.name] = source
    return mapping


def _parse_frame(raw: pd.DataFrame, contract: DatasetContract) -> tuple[pd.DataFrame, QualityReport]:
    """Map and validate a parsed tabular upload while retaining invalid rows for reporting."""
    mapping = infer_mapping(list(raw.columns), contract)
    normalized = pd.DataFrame(index=raw.index)
    for canonical, source in mapping.items():
        normalized[canonical] = raw[source]

    core_module = {
        "sales": BusinessModule.DEMAND,
        "inventory": BusinessModule.INVENTORY,
        "costs": BusinessModule.PROFITABILITY,
        "suppliers": BusinessModule.SUPPLIERS,
        "lots": BusinessModule.PERISHABLES,
    }[contract.key]
    required = {field.name for field in contract.required_columns(core_module)}
    missing_required = tuple(sorted(required - set(normalized.columns)))
    invalid_values: dict[str, int] = {}
    for field in contract.columns:
        if field.name not in normalized:
            continue
        if field.value_type is ValueType.DATE:
            converted = pd.to_datetime(normalized[field.name], errors="coerce")
            invalid_values[field.name] = int(converted.isna().sum())
            normalized[field.name] = converted
        elif field.value_type is ValueType.NUMBER:
            converted = pd.to_numeric(normalized[field.name], errors="coerce")
            invalid_values[field.name] = int(converted.isna().sum() + (converted < 0).sum())
            normalized[field.name] = converted
        elif field.value_type is ValueType.BOOLEAN:
            converted = normalized[field.name].astype(str).str.lower().map(
                {"true": True, "false": False, "1": True, "0": False, "si": True, "sí": True, "no": False}
            )
            invalid_values[field.name] = int(converted.isna().sum())
            normalized[field.name] = converted
        else:
            normalized[field.name] = normalized[field.name].astype("string").str.strip()
            invalid_values[field.name] = int(normalized[field.name].isna().sum() + normalized[field.name].eq("").sum())

    duplicate_rows = int(normalized.duplicated().sum())
    required_present = [column for column in required if column in normalized]
    valid_mask = pd.Series(True, index=normalized.index)
    if required_present:
        valid_mask &= normalized[required_present].notna().all(axis=1)
        for column in required_present:
            if pd.api.types.is_numeric_dtype(normalized[column]):
                valid_mask &= normalized[column] >= 0
            elif pd.api.types.is_string_dtype(normalized[column]):
                valid_mask &= normalized[column].ne("")
    report = QualityReport(
        mapped_columns=mapping,
        missing_required=missing_required,
        invalid_values={key: value for key, value in invalid_values.items() if value},
        duplicate_rows=duplicate_rows,
        valid_rows=int(valid_mask.sum()),
        total_rows=len(normalized),
    )
    return normalized, report


def parse_csv(uploaded_bytes: bytes, contract: DatasetContract) -> tuple[pd.DataFrame, QualityReport]:
    """Parse, map and validate a CSV while retaining invalid rows for transparent reporting."""
    return _parse_frame(pd.read_csv(BytesIO(uploaded_bytes)), contract)


def parse_tabular(uploaded_bytes: bytes, filename: str, contract: DatasetContract) -> tuple[pd.DataFrame, QualityReport]:
    """Parse a CSV or Excel upload through the same mapping and quality pipeline."""
    source = BytesIO(uploaded_bytes)
    if filename.lower().endswith(".xlsx"):
        return _parse_frame(pd.read_excel(source), contract)
    return _parse_frame(pd.read_csv(source), contract)


def parse_free_tabular(uploaded_bytes: bytes, filename: str) -> pd.DataFrame:
    """Parse a CSV or Excel file for generic EDA without dropping source columns."""
    source = BytesIO(uploaded_bytes)
    if filename.lower().endswith(".xlsx"):
        return pd.read_excel(source)
    return pd.read_csv(source)
