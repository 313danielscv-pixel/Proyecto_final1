from __future__ import annotations

import pandas as pd
import pytest

from src.bayesian_waste_risk import SNAPSHOT_COLUMNS, evaluate_bayesian_waste_risk


def _snapshot_data(include_unlabelled: bool = False) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for lot_number in range(40):
        label = int(lot_number < 20)
        for snapshot_number in range(2):
            row: dict[str, object] = {
                "lote_id": f"LOT-{lot_number:03}",
                "snapshot_date": f"2026-01-{snapshot_number + 1:02}",
                "tienda_nombre": f"STORE-{lot_number % 3}",
                "tipo_ubicacion": "refrigerado" if lot_number % 2 else "ambiente",
                "categoria": "perecedero" if label else "estable",
                "dias_vida_util": 4 + lot_number % 15,
                "dias_restantes": 2 + snapshot_number,
                "unidades_recibidas": 10 + lot_number,
                "stock_estimado": 5 + lot_number,
                "velocidad_venta_diaria": 0.2 + lot_number / 10,
                "precio_venta_base": 2.0 + lot_number / 10,
                "coste_unitario": 1.0 + lot_number / 20,
                "dia_semana": "lunes" if snapshot_number == 0 else "martes",
                "hubo_merma": pd.NA if include_unlabelled and lot_number == 40 else label,
            }
            rows.append(row)
    if include_unlabelled:
        for snapshot_number in range(2):
            row = {
                column: None for column in SNAPSHOT_COLUMNS
            }
            row.update(
                {
                    "lote_id": "LOT-040",
                    "snapshot_date": f"2026-01-{snapshot_number + 1:02}",
                    "tienda_nombre": "STORE-1",
                    "tipo_ubicacion": "refrigerado",
                    "categoria": "perecedero",
                    "dias_vida_util": 9,
                    "dias_restantes": 3 - snapshot_number,
                    "unidades_recibidas": 22,
                    "stock_estimado": 12,
                    "velocidad_venta_diaria": 0.8,
                    "precio_venta_base": 2.7,
                    "coste_unitario": 1.4,
                    "dia_semana": "lunes",
                    "hubo_merma": pd.NA,
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def test_bayesian_risk_validates_on_lots_separate_from_training() -> None:
    result = evaluate_bayesian_waste_risk(_snapshot_data())

    assert result["metrics"]["lotes_entrenamiento"] + result["metrics"]["lotes_validacion"] == 40
    assert result["metrics"]["auc_roc_por_lote"] >= 0.5
    assert result["predictions"]["tipo_resultado"].eq("validación").all()
    assert result["predictions"]["lote_id"].nunique() == result["metrics"]["lotes_validacion"]


def test_bayesian_risk_scores_unlabelled_lots_after_validation() -> None:
    result = evaluate_bayesian_waste_risk(_snapshot_data(include_unlabelled=True))

    unlabelled = result["predictions"].loc[
        result["predictions"]["tipo_resultado"].eq("lote sin etiqueta")
    ]
    assert unlabelled["lote_id"].unique().tolist() == ["LOT-040"]
    assert unlabelled["probabilidad_merma"].between(0, 1).all()


def test_bayesian_risk_requires_valid_labels_and_enough_lots() -> None:
    data = _snapshot_data()
    data["hubo_merma"] = 1
    with pytest.raises(ValueError, match="al menos 20 lotes"):
        evaluate_bayesian_waste_risk(data)

    with pytest.raises(ValueError, match="Faltan columnas"):
        evaluate_bayesian_waste_risk(pd.DataFrame({"lote_id": ["LOT-1"]}))


def test_bayesian_risk_rejects_inconsistent_lot_labels() -> None:
    data = _snapshot_data()
    data.loc[1, "hubo_merma"] = 1 - int(data.loc[0, "hubo_merma"])

    with pytest.raises(ValueError, match="única etiqueta"):
        evaluate_bayesian_waste_risk(data)
