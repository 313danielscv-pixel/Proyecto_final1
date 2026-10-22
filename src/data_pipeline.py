"""Create reproducible lot-level risk snapshots from the pilot database."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "raw" / "food_waste_pilot.db"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "risk_snapshots.csv"
DEFAULT_REPORT = ROOT / "data" / "processed" / "data_quality_report.json"


def load_pilot_tables(database_path: Path) -> dict[str, pd.DataFrame]:
    """Load the relational pilot tables required for feature construction."""
    with sqlite3.connect(database_path) as connection:
        return {
            table: pd.read_sql_query(f"SELECT * FROM {table}", connection)
            for table in ("tiendas", "productos", "lotes", "ventas", "mermas")
        }


def build_risk_snapshots(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build one prediction snapshot per lot and day remaining before expiry."""
    stores = tables["tiendas"].rename(columns={"nombre": "tienda_nombre"})
    products = tables["productos"]
    batches = tables["lotes"].copy()
    sales = tables["ventas"].copy()
    waste = tables["mermas"].copy()

    batches["fecha_recepcion"] = pd.to_datetime(batches["fecha_recepcion"])
    batches["fecha_caducidad"] = pd.to_datetime(batches["fecha_caducidad"])
    sales["fecha_hora_venta"] = pd.to_datetime(sales["fecha_hora_venta"])

    waste_by_batch = (
        waste.groupby("lote_id", as_index=False)
        .agg(unidades_mermadas=("unidades_mermadas", "sum"), coste_merma_eur=("coste_total_merma", "sum"))
    )
    enriched = (
        batches.merge(products, on="producto_id", validate="many_to_one")
        .merge(stores, on="tienda_id", validate="many_to_one")
        .merge(waste_by_batch, on="lote_id", how="left", validate="one_to_one")
    )
    enriched[["unidades_mermadas", "coste_merma_eur"]] = enriched[
        ["unidades_mermadas", "coste_merma_eur"]
    ].fillna(0)

    snapshots: list[dict[str, object]] = []
    for batch in enriched.itertuples(index=False):
        batch_sales = sales.loc[sales["lote_id"] == batch.lote_id].copy()
        for days_remaining in range(batch.dias_vida_util, -1, -1):
            snapshot_date = batch.fecha_caducidad - pd.Timedelta(days=days_remaining)
            past_sales = batch_sales.loc[batch_sales["fecha_hora_venta"] < snapshot_date]
            units_sold = int(past_sales["unidades_vendidas"].sum())
            elapsed_days = max(batch.dias_vida_util - days_remaining, 1)
            snapshots.append(
                {
                    "lote_id": batch.lote_id,
                    "snapshot_date": snapshot_date.date().isoformat(),
                    "tienda_nombre": batch.tienda_nombre,
                    "tipo_ubicacion": batch.tipo_ubicacion,
                    "categoria": batch.categoria,
                    "dias_vida_util": batch.dias_vida_util,
                    "dias_restantes": days_remaining,
                    "unidades_recibidas": batch.unidades_recibidas,
                    "stock_estimado": max(batch.unidades_recibidas - units_sold, 0),
                    "velocidad_venta_diaria": units_sold / elapsed_days,
                    "precio_venta_base": batch.precio_venta_base,
                    "coste_unitario": batch.coste_unitario,
                    "dia_semana": snapshot_date.day_name(),
                    "hubo_merma": int(batch.unidades_mermadas > 0),
                    "unidades_mermadas": batch.unidades_mermadas,
                    "coste_merma_eur": batch.coste_merma_eur,
                }
            )
    return pd.DataFrame(snapshots)


def quality_report(snapshots: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> dict[str, object]:
    """Summarize source and output quality checks for delivery documentation."""
    return {
        "source_type": "Synthetic operational pilot included with the project",
        "source_database": str(DEFAULT_DATABASE.relative_to(ROOT)),
        "source_rows": {name: int(len(frame)) for name, frame in tables.items()},
        "snapshot_rows": int(len(snapshots)),
        "duplicate_snapshots": int(snapshots.duplicated(subset=["lote_id", "snapshot_date"]).sum()),
        "null_values": {column: int(count) for column, count in snapshots.isna().sum().items() if count},
        "target_rate": round(float(snapshots["hubo_merma"].mean()), 4),
        "date_range": {
            "from": str(snapshots["snapshot_date"].min()),
            "to": str(snapshots["snapshot_date"].max()),
        },
    }


def run_pipeline(
    database_path: Path = DEFAULT_DATABASE,
    output_path: Path = DEFAULT_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
) -> pd.DataFrame:
    """Generate snapshots and persist their data-quality report."""
    tables = load_pilot_tables(database_path)
    snapshots = build_risk_snapshots(tables)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    snapshots.to_csv(output_path, index=False)
    report_path.write_text(
        json.dumps(quality_report(snapshots, tables), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return snapshots


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare ResQData risk snapshots.")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    arguments = parser.parse_args()
    result = run_pipeline(arguments.database, arguments.output, arguments.report)
    print(f"Created {len(result)} risk snapshots at {arguments.output}.")
