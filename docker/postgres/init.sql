\getenv reader_password RESQ_DEMO_POSTGRES_READONLY_PASSWORD
CREATE ROLE resq_reader LOGIN PASSWORD :'reader_password';

CREATE TABLE sales (
    date DATE NOT NULL,
    product_id TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2),
    store_id TEXT,
    category TEXT,
    promotion BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE inventory (
    snapshot_date DATE NOT NULL,
    product_id TEXT NOT NULL,
    on_hand_units INTEGER NOT NULL,
    unit_cost NUMERIC(10, 2),
    reorder_lead_days INTEGER,
    minimum_stock INTEGER,
    store_id TEXT,
    expiry_date DATE
);

CREATE TABLE costs (
    effective_date DATE,
    product_id TEXT NOT NULL,
    unit_cost NUMERIC(10, 2),
    unit_price NUMERIC(10, 2),
    holding_cost_per_unit_day NUMERIC(10, 4)
);

CREATE TABLE suppliers (
    supplier_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    lead_time_days INTEGER NOT NULL,
    minimum_order_quantity INTEGER,
    purchase_unit_cost NUMERIC(10, 2)
);

CREATE TABLE lots (
    lot_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    stock_available INTEGER NOT NULL,
    expiry_date DATE NOT NULL,
    unit_cost NUMERIC(10, 2) NOT NULL,
    store_id TEXT
);

INSERT INTO sales (date, product_id, quantity, unit_price, store_id, category, promotion)
VALUES
    ('2026-06-01', 'SKU-001', 18, 4.50, 'MAD-01', 'frescos', FALSE),
    ('2026-06-02', 'SKU-001', 21, 4.50, 'MAD-01', 'frescos', FALSE),
    ('2026-06-03', 'SKU-001', 16, 4.50, 'MAD-01', 'frescos', TRUE),
    ('2026-06-04', 'SKU-001', 24, 4.50, 'MAD-01', 'frescos', FALSE),
    ('2026-06-01', 'SKU-002', 12, 2.20, 'MAD-01', 'lacteos', FALSE),
    ('2026-06-02', 'SKU-002', 15, 2.20, 'MAD-01', 'lacteos', TRUE),
    ('2026-06-03', 'SKU-002', 11, 2.20, 'MAD-01', 'lacteos', FALSE),
    ('2026-06-04', 'SKU-002', 14, 2.20, 'MAD-01', 'lacteos', FALSE);

INSERT INTO inventory (snapshot_date, product_id, on_hand_units, unit_cost, reorder_lead_days, minimum_stock, store_id, expiry_date)
VALUES
    ('2026-06-04', 'SKU-001', 32, 2.10, 3, 12, 'MAD-01', '2026-06-10'),
    ('2026-06-04', 'SKU-002', 44, 1.05, 2, 10, 'MAD-01', '2026-06-18');

INSERT INTO costs (effective_date, product_id, unit_cost, unit_price, holding_cost_per_unit_day)
VALUES
    ('2026-06-01', 'SKU-001', 2.10, 4.50, 0.0150),
    ('2026-06-01', 'SKU-002', 1.05, 2.20, 0.0080);

INSERT INTO suppliers (supplier_id, product_id, lead_time_days, minimum_order_quantity, purchase_unit_cost)
VALUES
    ('SUP-001', 'SKU-001', 3, 10, 2.10),
    ('SUP-002', 'SKU-002', 2, 8, 1.05);

INSERT INTO lots (lot_id, product_id, stock_available, expiry_date, unit_cost, store_id)
VALUES
    ('LOT-001', 'SKU-001', 12, '2026-06-10', 2.10, 'MAD-01'),
    ('LOT-002', 'SKU-002', 18, '2026-06-18', 1.05, 'MAD-01');

GRANT CONNECT ON DATABASE resq_demo TO resq_reader;
GRANT USAGE ON SCHEMA public TO resq_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO resq_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO resq_reader;
