from __future__ import annotations

import pytest

from src.resqdata_case import load_resqdata_case


def test_resqdata_case_aggregates_the_synthetic_database() -> None:
    case = load_resqdata_case()
    summary = case["summary"].iloc[0]
    categories = case["categories"].set_index("categoria")

    assert summary["tiendas"] == 5
    assert summary["productos"] == 20
    assert summary["lotes"] == 3610
    assert summary["registros_venta"] == 16300
    assert summary["registros_merma"] == 1149
    assert summary["coste_merma_eur"] == pytest.approx(17422.1)
    assert categories.loc["Platos Preparados", "porcentaje_coste"] == pytest.approx(48.2)
    assert categories.loc["Pescadería", "porcentaje_coste"] == pytest.approx(15.9)
    assert case["top_products"].iloc[0]["producto"] == "Sushi Pack Variado 12 piezas"
