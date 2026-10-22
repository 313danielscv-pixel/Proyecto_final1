import pandas as pd

from src.reporting import build_analysis_report


def test_report_includes_quality_source_and_aggregates_without_raw_values() -> None:
    business_data = {
        "sales": pd.DataFrame(
            {
                "date": ["2026-01-01", "2026-01-02"],
                "product_id": ["SKU-1", "SKU-1"],
                "quantity": [3, 5],
                "note": ["private-note-a", "private-note-b"],
            }
        )
    }

    report = build_analysis_report(
        business_data,
        {},
        {"sales": "Ventas cargadas por la empresa"},
    )

    assert "Ventas cargadas por la empresa" in report
    assert "Unidades observadas: 8.00" in report
    assert "Celdas nulas: 0" in report
    assert "private-note-a" not in report
    assert "private-note-b" not in report


def test_report_documents_hypothetical_scenario_assumptions() -> None:
    report = build_analysis_report(
        {},
        {},
        {},
        {
            "price_change_pct": -10,
            "demand_change_pct": 15,
            "baseline_margin": 100.0,
            "scenario_margin": 110.0,
            "margin_change": 10.0,
        },
    )

    assert "Variación de precio asumida: -10 %" in report
    assert "Variación estimada: 10.00 €" in report
    assert "no predicciones ni ahorros realizados" in report


def test_report_includes_contract_validation_results() -> None:
    report = build_analysis_report(
        {"sales": pd.DataFrame({"product_id": ["SKU-1"]})},
        {},
        {"sales": "Archivo cargado por el usuario"},
        ingestion_reports={
            "sales": {
                "valid_rows": 2,
                "total_rows": 3,
                "missing_required": ("quantity",),
                "invalid_values": {"date": 1},
                "duplicate_rows": 1,
                "mapped_columns": {},
            }
        },
    )

    assert "2 de 3 filas aptas" in report
    assert "Campos obligatorios ausentes: quantity" in report
    assert "Conversiones o valores no válidos: date: 1" in report
