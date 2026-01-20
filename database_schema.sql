-- StockFlow Database Schema
-- Part 2: Database Design

-- Companies table
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Warehouses table
CREATE TABLE warehouses (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, name) -- Warehouse names unique per company
);

-- Suppliers table
CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Product Types table (for threshold configuration)
CREATE TABLE product_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    default_low_stock_threshold INTEGER NOT NULL DEFAULT 10,
    description TEXT
);

-- Products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(100) NOT NULL UNIQUE, -- SKU must be unique across platform
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    product_type_id INTEGER REFERENCES product_types(id),
    supplier_id INTEGER REFERENCES suppliers(id),
    is_bundle BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Product Bundles table (for bundle products)
CREATE TABLE product_bundles (
    id SERIAL PRIMARY KEY,
    bundle_product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    component_product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    UNIQUE(bundle_product_id, component_product_id),
    CHECK (bundle_product_id != component_product_id) -- Prevent self-reference
);

-- Inventory table (warehouse-product relationship)
CREATE TABLE inventory (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    low_stock_threshold INTEGER, -- Can override product type default
    last_restocked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, warehouse_id) -- One inventory record per product per warehouse
);

-- Inventory Transactions table (audit trail)
CREATE TABLE inventory_transactions (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
    transaction_type VARCHAR(50) NOT NULL, -- 'sale', 'restock', 'adjustment', 'transfer'
    quantity_change INTEGER NOT NULL, -- Positive for restock, negative for sale
    quantity_before INTEGER NOT NULL,
    quantity_after INTEGER NOT NULL,
    reference_id INTEGER, -- Order ID, transfer ID, etc.
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER -- User ID if you have users table
);

-- Sales table (to track recent sales activity)
CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    sale_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    order_id VARCHAR(100),
    customer_id INTEGER -- If tracking customers
);

-- Supplier Products table (which suppliers provide which products)
CREATE TABLE supplier_products (
    id SERIAL PRIMARY KEY,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    supplier_sku VARCHAR(100),
    cost_price DECIMAL(10, 2),
    lead_time_days INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(supplier_id, product_id)
);

-- Indexes for performance
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_supplier ON products(supplier_id);
CREATE INDEX idx_inventory_product_warehouse ON inventory(product_id, warehouse_id);
CREATE INDEX idx_inventory_warehouse ON inventory(warehouse_id);
CREATE INDEX idx_inventory_low_stock ON inventory(quantity, low_stock_threshold);
CREATE INDEX idx_sales_product_date ON sales(product_id, sale_date DESC);
CREATE INDEX idx_sales_warehouse_date ON sales(warehouse_id, sale_date DESC);
CREATE INDEX idx_inventory_transactions_product ON inventory_transactions(product_id, warehouse_id, created_at DESC);
CREATE INDEX idx_warehouses_company ON warehouses(company_id);

-- Additional useful indexes
CREATE INDEX idx_products_product_type ON products(product_type_id);
CREATE INDEX idx_sales_date ON sales(sale_date DESC);
CREATE INDEX idx_inventory_transactions_type ON inventory_transactions(transaction_type);

