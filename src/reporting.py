"""Build shareable summaries from the current in-memory analysis session."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

import pandas as pd

from src.advanced_eda import profile_data, quality_summary
from src.business_intelligence import (
    attach_cost_reference,
    average_daily_demand,
    inventory_intelligence,
)
from src.contracts import COSTS_CONTRACT, INVENTORY_CONTRACT, LOTS_CONTRACT, SALES_CONTRACT
from src.lot_risk import build_lot_risk


def _markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _date_period(data: pd.DataFrame, column: str = "date") -> str:
    candidates = [column] if column in data else []
    candidates.extend(
        candidate
        for candidate in data.columns
        if candidate not in candidates
        and any(token in str(candidate).lower() for token in ("date", "fecha", "datetime", "timestamp"))
    )
    for candidate in candidates:
        dates = pd.to_datetime(data[candidate], errors="coerce").dropna()
        if not dates.empty:
            return f"{dates.min().date().isoformat()} a {dates.max().date().isoformat()}"
    return "No disponible"


def build_analysis_report(
    business_data: Mapping[str, pd.DataFrame],
    free_eda_data: Mapping[str, pd.DataFrame],
    source_labels: Mapping[str, str],
    scenario: Mapping[str, object] | None = None,
    ingestion_reports: Mapping[str, Mapping[str, object]] | None = None,
) -> str:
    """Create a Markdown report with quality, available business results and limitations."""
    datasets = {**business_data, **free_eda_data}
    ingestion_reports = ingestion_reports or {}
    generated_at = datetime.now().astimezone().isoformat(timespec="minutes")
    lines = [
        "# Informe de análisis — ResQ Intelligence",
        "",
        f"Generado: {generated_at}",
        "",
        "Este informe resume los datos cargados en la sesión. No incluye filas originales ni datos de ejemplo.",
        "",
        "## Resumen de calidad y procedencia",
        "",
    ]
    for name, data in sorted(datasets.items()):
        report = quality_summary(data)
        source = source_labels.get(name, "Origen no registrado; verificar antes de compartir.")
        lines.extend(
            [
                f"### {_markdown_cell(name)}",
                "",
                f"- Procedencia: {_markdown_cell(source)}",
                f"- Filas: {report['rows']:,}; columnas: {report['columns']:,}.",
                f"- Celdas nulas: {report['missing_cells']:,}; filas duplicadas: {report['duplicate_rows']:,}.",
                f"- Periodo observado: {_date_period(data)}.",
                "",
                "| Columna | Tipo detectado | Nulos | Porcentaje nulo |",
                "|---|---|---:|---:|",
            ]
        )
        for row in profile_data(data).itertuples(index=False):
            lines.append(
                f"| {_markdown_cell(row.columna)} | {_markdown_cell(row.tipo)} | "
                f"{row.filas_nulas:,} | {row.porcentaje_nulo:.1%} |"
            )
        if report["negative_values"]:
            negative = ", ".join(
                f"{_markdown_cell(column)}: {count:,}"
                for column, count in report["negative_values"].items()
            )
            lines.extend(["", f"- Valores negativos que requieren revisión: {negative}."])
        if report["potential_leakage_columns"]:
            columns = ", ".join(map(_markdown_cell, report["potential_leakage_columns"]))
            lines.extend(["", f"- Posibles columnas a revisar por nombre: {columns}."])
        ingestion = ingestion_reports.get(name)
        if ingestion:
            lines.append(
                f"- Validación por contrato: {ingestion['valid_rows']:,} de "
                f"{ingestion['total_rows']:,} filas aptas."
            )
            missing_required = ingestion["missing_required"]
            if missing_required:
                missing = ", ".join(map(_markdown_cell, missing_required))
                lines.append(f"- Campos obligatorios ausentes: {missing}.")
            invalid_values = ingestion["invalid_values"]
            if invalid_values:
                invalid = ", ".join(
                    f"{_markdown_cell(column)}: {count:,}"
                    for column, count in invalid_values.items()
                )
                lines.append(f"- Conversiones o valores no válidos: {invalid}.")
            if ingestion["duplicate_rows"]:
                lines.append(f"- Filas duplicadas detectadas en la carga: {ingestion['duplicate_rows']:,}.")
            mapped_columns = ingestion["mapped_columns"]
            if mapped_columns:
                mapping = ", ".join(
                    f"{_markdown_cell(source)} → {_markdown_cell(target)}"
                    for source, target in mapped_columns.items()
                )
                lines.append(f"- Mapeo de columnas: {mapping}.")
        lines.append("")

    sales = business_data.get(SALES_CONTRACT.key)
    costs = business_data.get(COSTS_CONTRACT.key)
    if sales is not None and {"date", "product_id", "quantity"}.issubset(sales.columns):
        valid_sales = sales.dropna(subset=["date", "product_id", "quantity"]).copy()
        quantities = pd.to_numeric(valid_sales["quantity"], errors="coerce").dropna()
        lines.extend(
            [
                "## Actividad de ventas",
                "",
                f"- Unidades observadas: {quantities.sum():,.2f}.",
                f"- Productos distintos: {valid_sales['product_id'].nunique():,}.",
                f"- Periodo: {_date_period(valid_sales)}.",
            ]
        )
        valued_sales = attach_cost_reference(valid_sales, costs)
        if {"unit_price", "unit_cost"}.issubset(valued_sales.columns):
            valued_sales["quantity"] = pd.to_numeric(valued_sales["quantity"], errors="coerce")
            valued_sales["unit_price"] = pd.to_numeric(valued_sales["unit_price"], errors="coerce")
            valued_sales["unit_cost"] = pd.to_numeric(valued_sales["unit_cost"], errors="coerce")
            valid_margin = valued_sales.dropna(subset=["quantity", "unit_price", "unit_cost"])
            if not valid_margin.empty:
                margin = (
                    valid_margin["quantity"]
                    * (valid_margin["unit_price"] - valid_margin["unit_cost"])
                ).sum()
                cost_source = source_labels.get(COSTS_CONTRACT.key, "").lower()
                if "supuesto" in cost_source or "sintético" in cost_source or "sintetico" in cost_source:
                    lines.append(
                        f"- Margen bruto de escenario, con precio y coste supuestos: {margin:,.2f} €."
                    )
                else:
                    lines.append(f"- Margen bruto estimado bajo los precios y costes cargados: {margin:,.2f} €.")
            else:
                lines.append("- Margen bruto: no calculado; faltan precios o costes válidos.")
        else:
            lines.append("- Margen bruto: no calculado; se necesitan precio y coste unitario.")
        lines.extend(["", "Estas cifras describen las filas cargadas; no son una previsión.", ""])

    inventory = business_data.get(INVENTORY_CONTRACT.key)
    if (
        inventory is not None
        and sales is not None
        and {"product_id", "on_hand_units"}.issubset(inventory.columns)
        and {"date", "product_id", "quantity"}.issubset(sales.columns)
    ):
        enriched_inventory = attach_cost_reference(inventory, costs)
        intelligence = inventory_intelligence(enriched_inventory, average_daily_demand(sales))
        lines.extend(["## Inventario", ""])
        if "unit_cost" in intelligence:
            capital = pd.to_numeric(intelligence["capital_exposed"], errors="coerce").sum()
            cost_source = source_labels.get(COSTS_CONTRACT.key, "").lower()
            if "supuesto" in cost_source or "sintético" in cost_source or "sintetico" in cost_source:
                lines.append(f"- Capital expuesto de escenario con coste supuesto: {capital:,.2f} €.")
            else:
                lines.append(f"- Capital expuesto estimado: {capital:,.2f} €.")
        else:
            lines.append("- Capital expuesto: no calculado; falta un coste unitario válido.")
        lines.extend(
            [
                f"- Productos con señal de rotura: {intelligence['risk'].eq('rotura').sum():,}.",
                f"- Productos con señal de sobrestock: {intelligence['risk'].eq('sobrestock').sum():,}.",
                "",
                "La demanda usa la media por producto y día observado. Los días sin ventas no se imputan como cero.",
                "",
            ]
        )
    lots = business_data.get(LOTS_CONTRACT.key)
    lot_columns = {"lot_id", "product_id", "stock_available", "expiry_date", "unit_cost"}
    if lots is not None and sales is not None and lot_columns.issubset(lots.columns):
        risks, warnings = build_lot_risk(lots, sales)
        lines.extend(["## Riesgo por lote", ""])
        if risks.empty:
            lines.append("- No hay lotes con historial suficiente para estimar el indicador.")
        else:
            valid_risks = risks.dropna(subset=["estimated_unsold_stock_ratio"])
            if valid_risks.empty:
                lines.append("- No hay lotes con historial suficiente para estimar el indicador.")
            else:
                priority_count = int(valid_risks["estimated_unsold_stock_ratio"].ge(0.60).sum())
                lines.extend(
                    [
                        f"- Lotes analizados: {len(valid_risks):,}.",
                        f"- Lotes prioritarios según el umbral exploratorio: {priority_count:,}.",
                        f"- Coste expuesto estimado: {valid_risks['cost_exposed'].sum():,.2f} €.",
                        "- El indicador es una proporción estimada de stock no vendido, no una probabilidad calibrada ni una merma confirmada.",
                    ]
                )
        if warnings:
            lines.append(f"- Avisos: {_markdown_cell(' '.join(warnings))}")
        lines.append("")

    if scenario:
        lines.extend(
            [
                "## Escenario económico",
                "",
                f"- Variación de precio asumida: {scenario['price_change_pct']} %.",
                f"- Variación de demanda asumida: {scenario['demand_change_pct']} %.",
                f"- Margen base estimado: {scenario['baseline_margin']:,.2f} €.",
                f"- Margen del escenario: {scenario['scenario_margin']:,.2f} €.",
                f"- Variación estimada: {scenario['margin_change']:,.2f} €.",
                "",
                "Son supuestos del usuario, no predicciones ni ahorros realizados.",
                "",
            ]
        )

    lines.extend(
        [
            "## Limitaciones",
            "",
            "- Los análisis describen los datos cargados; correlación y anomalías no demuestran causalidad.",
            "- Los resultados dependen de la calidad, cobertura temporal y reglas de negocio de los archivos.",
            "- La demo distingue las ventas derivadas de FreshRetailNet de los supuestos de inventario, costes y lotes.",
            "- Los archivos cargados permanecen en la sesión; este informe se genera en memoria al solicitar la descarga.",
            "",
        ]
    )
    return "\n".join(lines)
