"""Read-only summaries for the synthetic ResQ Data FreshMarket case."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd


DEMO_DATABASE_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "demo"
    / "resqdata_freshmarket_synthetic.db"
)


def load_resqdata_case(database_path: Path = DEMO_DATABASE_PATH) -> dict[str, pd.DataFrame]:
    """Load aggregate business summaries without modifying the bundled database."""
    if not database_path.is_file():
        raise FileNotFoundError(f"ResQ Data demo database not found: {database_path}")

    database_uri = f"{database_path.resolve().as_uri()}?mode=ro"
    with closing(sqlite3.connect(database_uri, uri=True)) as connection:
        summary = pd.read_sql_query(
            """
            SELECT
                (SELECT COUNT(*) FROM tiendas) AS tiendas,
                (SELECT COUNT(*) FROM productos) AS productos,
                (SELECT COUNT(*) FROM lotes) AS lotes,
                (SELECT COUNT(*) FROM ventas) AS registros_venta,
                (SELECT COUNT(DISTINCT date(fecha_hora_venta)) FROM ventas) AS dias_venta,
                (SELECT COUNT(*) FROM mermas) AS registros_merma,
                (SELECT SUM(unidades_mermadas) FROM mermas) AS unidades_mermadas,
                (SELECT SUM(coste_total_merma) FROM mermas) AS coste_merma_eur,
                (SELECT COUNT(*) FROM donaciones) AS registros_donacion,
                (SELECT SUM(unidades_donadas) FROM donaciones) AS unidades_donadas,
                (SELECT SUM(valor_donacion) FROM donaciones) AS valor_donacion_eur
            """,
            connection,
        )
        categories = pd.read_sql_query(
            """
            SELECT
                p.categoria AS categoria,
                SUM(m.unidades_mermadas) AS unidades_mermadas,
                ROUND(SUM(m.coste_total_merma), 2) AS coste_merma_eur,
                ROUND(
                    100.0 * SUM(m.coste_total_merma) /
                    (SELECT SUM(coste_total_merma) FROM mermas),
                    1
                ) AS porcentaje_coste
            FROM mermas AS m
            JOIN lotes AS l ON m.lote_id = l.lote_id
            JOIN productos AS p ON l.producto_id = p.producto_id
            GROUP BY p.categoria
            ORDER BY coste_merma_eur DESC
            """,
            connection,
        )
        stores = pd.read_sql_query(
            """
            SELECT
                t.nombre AS tienda,
                t.ciudad AS ciudad,
                COUNT(m.merma_id) AS registros_merma,
                SUM(m.unidades_mermadas) AS unidades_mermadas,
                ROUND(SUM(m.coste_total_merma), 2) AS coste_merma_eur
            FROM mermas AS m
            JOIN tiendas AS t ON m.tienda_id = t.tienda_id
            GROUP BY t.tienda_id
            ORDER BY coste_merma_eur DESC
            """,
            connection,
        )
        top_products = pd.read_sql_query(
            """
            SELECT
                p.nombre AS producto,
                p.categoria AS categoria,
                SUM(m.unidades_mermadas) AS unidades_mermadas,
                ROUND(SUM(m.coste_total_merma), 2) AS coste_merma_eur
            FROM mermas AS m
            JOIN lotes AS l ON m.lote_id = l.lote_id
            JOIN productos AS p ON l.producto_id = p.producto_id
            GROUP BY p.producto_id
            ORDER BY coste_merma_eur DESC
            LIMIT 5
            """,
            connection,
        )
    return {
        "summary": summary,
        "categories": categories,
        "stores": stores,
        "top_products": top_products,
    }
