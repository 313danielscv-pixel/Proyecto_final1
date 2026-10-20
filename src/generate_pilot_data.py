import sqlite3
import random
from datetime import datetime, timedelta

def build_database():
    conn = sqlite3.connect('food_waste.db')
    cursor = conn.cursor()

    # Enable FKs
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Drop existing tables if re-running
    cursor.executescript("""
        DROP TABLE IF EXISTS donaciones;
        DROP TABLE IF EXISTS mermas;
        DROP TABLE IF EXISTS ventas;
        DROP TABLE IF EXISTS lotes;
        DROP TABLE IF EXISTS productos;
        DROP TABLE IF EXISTS tiendas;

        CREATE TABLE tiendas (
            tienda_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            ciudad TEXT NOT NULL,
            superficie_m2 INTEGER NOT NULL,
            tipo_ubicacion TEXT NOT NULL
        );

        CREATE TABLE productos (
            producto_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            dias_vida_util INTEGER NOT NULL,
            precio_venta_base REAL NOT NULL,
            coste_unitario REAL NOT NULL,
            temperatura_conservacion TEXT NOT NULL
        );

        CREATE TABLE lotes (
            lote_id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            tienda_id INTEGER NOT NULL,
            unidades_recibidas INTEGER NOT NULL,
            unidades_disponibles INTEGER NOT NULL,
            fecha_recepcion DATE NOT NULL,
            fecha_caducidad DATE NOT NULL,
            FOREIGN KEY (producto_id) REFERENCES productos(producto_id),
            FOREIGN KEY (tienda_id) REFERENCES tiendas(tienda_id)
        );

        CREATE TABLE ventas (
            venta_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lote_id INTEGER NOT NULL,
            tienda_id INTEGER NOT NULL,
            unidades_vendidas INTEGER NOT NULL,
            precio_unidades_real REAL NOT NULL,
            descuento_aplicado_pct REAL NOT NULL,
            fecha_hora_venta DATETIME NOT NULL,
            FOREIGN KEY (lote_id) REFERENCES lotes(lote_id),
            FOREIGN KEY (tienda_id) REFERENCES tiendas(tienda_id)
        );

        CREATE TABLE mermas (
            merma_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lote_id INTEGER NOT NULL,
            tienda_id INTEGER NOT NULL,
            unidades_mermadas INTEGER NOT NULL,
            coste_total_merma REAL NOT NULL,
            motivo_merma TEXT NOT NULL,
            fecha_merma DATE NOT NULL,
            FOREIGN KEY (lote_id) REFERENCES lotes(lote_id),
            FOREIGN KEY (tienda_id) REFERENCES tiendas(tienda_id)
        );

        CREATE TABLE donaciones (
            donacion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lote_id INTEGER NOT NULL,
            tienda_id INTEGER NOT NULL,
            unidades_donadas INTEGER NOT NULL,
            ong_beneficiaria TEXT NOT NULL,
            valor_donacion REAL NOT NULL,
            fecha_donacion DATE NOT NULL,
            FOREIGN KEY (lote_id) REFERENCES lotes(lote_id),
            FOREIGN KEY (tienda_id) REFERENCES tiendas(tienda_id)
        );
    """)

    # Seed Tiendas (5 tiendas representativas)
    tiendas_data = [
        ('FreshMarket Centro Madrid', 'Madrid', 1200, 'Urbano Premium'),
        ('FreshMarket Vallecas', 'Madrid', 850, 'Residencial'),
        ('FreshMarket Sarrià', 'Barcelona', 1100, 'Urbano Premium'),
        ('FreshMarket Eixample', 'Barcelona', 950, 'Urbano Comercial'),
        ('FreshMarket Ruzafa', 'Valencia', 900, 'Urbano Mixto')
    ]
    cursor.executemany("INSERT INTO tiendas (nombre, ciudad, superficie_m2, tipo_ubicacion) VALUES (?,?,?,?)", tiendas_data)

    # Seed Productos (20 productos frescos de alta rotación / merma)
    productos_data = [
        ('Pechuga de Pollo Fresca 500g', 'Carnicería', 6, 4.95, 2.80, 'Refrigerado'),
        ('Lomo de Salmón Noruego 400g', 'Pescadería', 5, 8.50, 5.10, 'Refrigerado'),
        ('Ensalada César Preparada 250g', 'Platos Preparados', 4, 3.20, 1.50, 'Refrigerado'),
        ('Yogur Griego Natural 4x125g', 'Lácteos', 14, 2.10, 1.10, 'Refrigerado'),
        ('Leche Entera Célere 1L', 'Lácteos', 10, 1.05, 0.65, 'Refrigerado'),
        ('Fresones de Huelva 500g', 'Frutas y Verduras', 5, 3.49, 1.80, 'Ambiente/Fresco'),
        ('Aguacate Malla 3ud', 'Frutas y Verduras', 7, 2.99, 1.40, 'Ambiente/Fresco'),
        ('Manzana Golden Bolsa 1.5kg', 'Frutas y Verduras', 12, 2.40, 1.10, 'Ambiente/Fresco'),
        ('Sushi Pack Variado 12 piezas', 'Platos Preparados', 3, 9.90, 5.20, 'Refrigerado'),
        ('Carne Picada Vacuno 400g', 'Carnicería', 5, 4.20, 2.30, 'Refrigerado'),
        ('Pan de Masa Madre 400g', 'Panadería', 2, 1.80, 0.50, 'Ambiente'),
        ('Empanada de Atún Artesana', 'Panadería', 3, 3.50, 1.30, 'Ambiente'),
        ('Queso Fresco de Burgos 250g', 'Lácteos', 8, 2.15, 1.15, 'Refrigerado'),
        ('Zumo de Naranja Recién Exprimido 1L', 'Bebidas Frescas', 4, 3.80, 1.90, 'Refrigerado'),
        ('Hamburguesa de Pavo/Espinacas 2ud', 'Carnicería', 6, 3.60, 1.95, 'Refrigerado'),
        ('Dorada Limpia Ración 300g', 'Pescadería', 4, 5.40, 3.10, 'Refrigerado'),
        ('Plátano de Canarias 1kg', 'Frutas y Verduras', 6, 1.99, 0.90, 'Ambiente'),
        ('Hummus Tradicional 200g', 'Platos Preparados', 10, 1.75, 0.85, 'Refrigerado'),
        ('Nata para Montar 200ml', 'Lácteos', 15, 1.25, 0.60, 'Refrigerado'),
        ('Tarta Red Velvet Ración', 'Pastelería', 4, 3.90, 1.80, 'Refrigerado')
    ]
    cursor.executemany("""
        INSERT INTO productos (nombre, categoria, dias_vida_util, precio_venta_base, coste_unitario, temperatura_conservacion)
        VALUES (?,?,?,?,?,?)
    """, productos_data)

    # Generate synthetic historical dataset for 90 days
    start_date = datetime(2026, 6, 1)
    
    random.seed(42)

    lote_id = 1
    # Generate batch receipts
    for day in range(90):
        current_date = start_date + timedelta(days=day)
        date_str = current_date.strftime('%Y-%m-%d')

        for t_id in range(1, 6):
            # Each store receives batches of random products
            # Sample 6-10 products received per day
            selected_prods = random.sample(range(1, 21), k=random.randint(6, 10))
            for p_id in selected_prods:
                # fetch product life
                cursor.execute("SELECT dias_vida_util, precio_venta_base, coste_unitario FROM productos WHERE producto_id = ?", (p_id,))
                prod = cursor.fetchone()
                vida_util, p_venta, coste = prod

                unidades = random.randint(15, 60)
                expiry_date = current_date + timedelta(days=vida_util)
                expiry_str = expiry_date.strftime('%Y-%m-%d')

                cursor.execute("""
                    INSERT INTO lotes (producto_id, tienda_id, unidades_recibidas, unidades_disponibles, fecha_recepcion, fecha_caducidad)
                    VALUES (?,?,?,?,?,?)
                """, (p_id, t_id, unidades, unidades, date_str, expiry_str))

                # Simulate daily sales / mermas for this batch over its shelf life
                units_left = unidades
                batch_id = cursor.lastrowid

                # Days alive
                for d_offset in range(vida_util + 1):
                    day_sim = current_date + timedelta(days=d_offset)
                    if day_sim > datetime(2026, 8, 31):
                        break
                    
                    days_to_expiry = vida_util - d_offset
                    day_sim_str = day_sim.strftime('%Y-%m-%d')

                    if units_left <= 0:
                        break

                    # Behavior pattern:
                    # Near expiry (days_to_expiry <= 1): if discount applied, high sales; if not, high waste!
                    # Problem pattern: Currently store #2 (Vallecas) and store #5 (Ruzafa) apply manual discounts late (day 0), causing huge waste!
                    # Platos preparados and Pescadería have huge waste on Monday-Wednesday.
                    
                    if days_to_expiry > 2:
                        sell_pct = random.uniform(0.15, 0.35)
                        unid_sell = min(units_left, int(unidades * sell_pct))
                        discount = 0.0
                    elif days_to_expiry == 2:
                        sell_pct = random.uniform(0.10, 0.25)
                        unid_sell = min(units_left, int(unidades * sell_pct))
                        discount = 0.0
                    elif days_to_expiry == 1:
                        # 30% discount applied manually in some stores
                        if t_id in [1, 3]:
                            discount = 0.30
                            sell_pct = random.uniform(0.40, 0.60)
                        else:
                            discount = 0.0
                            sell_pct = random.uniform(0.10, 0.20)
                        unid_sell = min(units_left, int(unidades * sell_pct))
                    else: # day 0 (expiration day)
                        if t_id in [1, 3]:
                            discount = 0.50
                            sell_pct = random.uniform(0.50, 0.70)
                            unid_sell = min(units_left, int(units_left * sell_pct))
                        else:
                            discount = 0.20
                            sell_pct = random.uniform(0.10, 0.25)
                            unid_sell = min(units_left, int(units_left * sell_pct))

                    if unid_sell > 0:
                        real_price = round(p_venta * (1.0 - discount), 2)
                        sale_dt = f"{day_sim_str} {random.randint(9, 21):02d}:{random.randint(0,59):02d}:00"
                        cursor.execute("""
                            INSERT INTO ventas (lote_id, tienda_id, unidades_vendidas, precio_unidades_real, descuento_aplicado_pct, fecha_hora_venta)
                            VALUES (?,?,?,?,?,?)
                        """, (batch_id, t_id, unid_sell, real_price, discount, sale_dt))
                        units_left -= unid_sell

                    # If expired today, remaining goes to merma or donacion
                    if days_to_expiry == 0 and units_left > 0:
                        # 80% waste, 20% donation
                        donated = int(units_left * 0.20) if units_left >= 5 else 0
                        wasted = units_left - donated

                        if wasted > 0:
                            coste_merma = round(wasted * coste, 2)
                            cursor.execute("""
                                INSERT INTO mermas (lote_id, tienda_id, unidades_mermadas, coste_total_merma, motivo_merma, fecha_merma)
                                VALUES (?,?,?,?,?,?)
                            """, (batch_id, t_id, wasted, coste_merma, 'Caducidad / Cadena de Frío', day_sim_str))

                        if donated > 0:
                            val_don = round(donated * coste, 2)
                            cursor.execute("""
                                INSERT INTO donaciones (lote_id, tienda_id, unidades_donadas, ong_beneficiaria, valor_donacion, fecha_donacion)
                                VALUES (?,?,?,?,?,?)
                            """, (batch_id, t_id, donated, 'Banco de Alimentos Local', val_don, day_sim_str))

                        units_left = 0

                # Update remaining
                cursor.execute("UPDATE lotes SET unidades_disponibles = ? WHERE lote_id = ?", (max(0, units_left), batch_id))

    conn.commit()

    # Print summary
    cursor.execute("SELECT COUNT(*) FROM lotes")
    tot_lotes = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM ventas")
    tot_ventas = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(coste_total_merma) FROM mermas")
    tot_merma_eur = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(valor_donacion) FROM donaciones")
    tot_donacion_eur = cursor.fetchone()[0]

    print(f"Base de datos 'food_waste.db' creada exitosamente.")
    print(f"Total Lotes registrados: {tot_lotes}")
    print(f"Total Operaciones de Venta: {tot_ventas}")
    print(f"Coste Total Merma Acumulada: {tot_merma_eur:,.2f} €")
    print(f"Valor Total Donaciones: {tot_donacion_eur:,.2f} €")

    conn.close()

if __name__ == '__main__':
    build_database()
