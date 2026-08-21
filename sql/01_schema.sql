PRAGMA foreign_keys = ON;

CREATE TABLE warehouses (
    warehouse_id TEXT PRIMARY KEY,
    city TEXT NOT NULL UNIQUE,
    region TEXT NOT NULL
);

CREATE TABLE suppliers (
    supplier_id TEXT PRIMARY KEY,
    supplier_name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    base_delay_risk REAL NOT NULL CHECK (base_delay_risk BETWEEN 0 AND 1),
    base_reject_risk REAL NOT NULL CHECK (base_reject_risk BETWEEN 0 AND 1)
);

CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    unit_cost REAL NOT NULL CHECK (unit_cost > 0),
    list_price REAL NOT NULL CHECK (list_price >= unit_cost),
    shelf_life_days INTEGER NOT NULL CHECK (shelf_life_days > 0),
    cold_chain_required INTEGER NOT NULL CHECK (cold_chain_required IN (0, 1)),
    primary_supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id)
);

CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    city TEXT NOT NULL,
    business_type TEXT NOT NULL CHECK (
        business_type IN ('Restaurant', 'Cloud Kitchen', 'Cafe & Bakery', 'Caterer')
    ),
    joined_date TEXT NOT NULL
);

CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    warehouse_id TEXT NOT NULL REFERENCES warehouses(warehouse_id),
    order_date TEXT NOT NULL,
    promised_date TEXT NOT NULL,
    delivered_date TEXT,
    delivery_model TEXT NOT NULL CHECK (delivery_model IN ('Next-day', 'Express')),
    order_status TEXT NOT NULL CHECK (order_status IN ('Delivered', 'Cancelled')),
    failure_reason TEXT NOT NULL,
    CHECK (promised_date >= order_date),
    CHECK (
        (order_status = 'Delivered' AND delivered_date IS NOT NULL)
        OR (order_status = 'Cancelled' AND delivered_date IS NULL)
    )
);

CREATE TABLE order_items (
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    line_number INTEGER NOT NULL CHECK (line_number > 0),
    product_id TEXT NOT NULL REFERENCES products(product_id),
    ordered_qty INTEGER NOT NULL CHECK (ordered_qty > 0),
    fulfilled_qty INTEGER NOT NULL CHECK (fulfilled_qty BETWEEN 0 AND ordered_qty),
    selling_price REAL NOT NULL CHECK (selling_price > 0),
    unit_cost REAL NOT NULL CHECK (unit_cost > 0),
    PRIMARY KEY (order_id, line_number)
);

CREATE TABLE procurement_receipts (
    receipt_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id),
    warehouse_id TEXT NOT NULL REFERENCES warehouses(warehouse_id),
    product_id TEXT NOT NULL REFERENCES products(product_id),
    expected_date TEXT NOT NULL,
    received_date TEXT NOT NULL,
    ordered_qty INTEGER NOT NULL CHECK (ordered_qty > 0),
    received_qty INTEGER NOT NULL CHECK (received_qty BETWEEN 0 AND ordered_qty),
    rejected_qty INTEGER NOT NULL CHECK (rejected_qty BETWEEN 0 AND received_qty),
    unit_cost REAL NOT NULL CHECK (unit_cost > 0)
);

CREATE TABLE waste_events (
    event_id TEXT PRIMARY KEY,
    event_date TEXT NOT NULL,
    warehouse_id TEXT NOT NULL REFERENCES warehouses(warehouse_id),
    product_id TEXT NOT NULL REFERENCES products(product_id),
    reason TEXT NOT NULL CHECK (reason IN ('Expiry', 'Spoilage', 'Handling damage')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_cost REAL NOT NULL CHECK (unit_cost > 0)
);

CREATE INDEX idx_orders_date_warehouse ON orders(order_date, warehouse_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_receipts_date_supplier ON procurement_receipts(expected_date, supplier_id);
CREATE INDEX idx_waste_date_product ON waste_events(event_date, product_id);
