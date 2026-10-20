import sqlite3
import pandas as pd

def run_eda():
    conn = sqlite3.connect('food_waste.db')

    print("=== 1. MERMA TOTAL POR TIENDA ===")
    df_tiendas = pd.read_sql_query("""
        SELECT t.nombre, t.ciudad, COUNT(m.merma_id) as num_mermas, 
               SUM(m.unidades_mermadas) as unid_mermadas, 
               SUM(m.coste_total_merma) as coste_merma_eur
        FROM mermas m
        JOIN tiendas t ON m.tienda_id = t.tienda_id
        GROUP BY t.tienda_id
        ORDER BY coste_merma_eur DESC
    """, conn)
    print(df_tiendas.to_string(index=False))

    print("\n=== 2. MERMA TOTAL POR CATEGORÍA DE PRODUCTO ===")
    df_cat = pd.read_sql_query("""
        SELECT p.categoria, SUM(m.unidades_mermadas) as unid_mermadas,
               SUM(m.coste_total_merma) as coste_merma_eur,
               ROUND(AVG(m.coste_total_merma / m.unidades_mermadas), 2) as coste_medio_unidad
        FROM mermas m
        JOIN lotes l ON m.lote_id = l.lote_id
        JOIN productos p ON l.producto_id = p.producto_id
        GROUP BY p.categoria
        ORDER BY coste_merma_eur DESC
    """, conn)
    print(df_cat.to_string(index=False))

    print("\n=== 3. TOP 5 PRODUCTOS CON MAYOR PÉRDIDA ===")
    df_top_prod = pd.read_sql_query("""
        SELECT p.nombre, p.categoria, SUM(m.unidades_mermadas) as unid_mermadas,
               SUM(m.coste_total_merma) as coste_merma_eur
        FROM mermas m
        JOIN lotes l ON m.lote_id = l.lote_id
        JOIN productos p ON l.producto_id = p.producto_id
        GROUP BY p.producto_id
        ORDER BY coste_merma_eur DESC
        LIMIT 5
    """, conn)
    print(df_top_prod.to_string(index=False))

    print("\n=== 4. COMPARATIVA DE TIENDAS Y POLÍTICA DE DESCUENTOS ===")
    df_desc = pd.read_sql_query("""
        SELECT 
            t.nombre as tienda,
            ROUND(AVG(v.descuento_aplicado_pct) * 100, 1) as descuento_medio_pct,
            (SELECT ROUND(SUM(coste_total_merma), 2) FROM mermas WHERE tienda_id = t.tienda_id) as total_merma_eur,
            (SELECT ROUND(SUM(valor_donacion), 2) FROM donaciones WHERE tienda_id = t.tienda_id) as total_donacion_eur
        FROM tiendas t
        LEFT JOIN ventas v ON t.tienda_id = v.tienda_id
        GROUP BY t.tienda_id
    """, conn)
    print(df_desc.to_string(index=False))

    conn.close()

if __name__ == '__main__':
    run_eda()
