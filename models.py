"""
SQLAlchemy models for StockFlow inventory management system.
These models correspond to the database schema defined in database_schema.sql
"""

from sqlalchemy import Column, Integer, String, Decimal, Boolean, Text, ForeignKey, CheckConstraint, UniqueConstraint, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Company(Base):
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    warehouses = relationship("Warehouse", back_populates="company", cascade="all, delete-orphan")


class Warehouse(Base):
    __tablename__ = 'warehouses'
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="warehouses")
    inventory = relationship("Inventory", back_populates="warehouse")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('company_id', 'name', name='uq_warehouse_company_name'),
    )


class Supplier(Base):
    __tablename__ = 'suppliers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    contact_email = Column(String(255))
    contact_phone = Column(String(50))
    address = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    products = relationship("Product", back_populates="supplier")
    supplier_products = relationship("SupplierProduct", back_populates="supplier")


class ProductType(Base):
    __tablename__ = 'product_types'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    default_low_stock_threshold = Column(Integer, nullable=False, default=10)
    description = Column(Text)
    
    # Relationships
    products = relationship("Product", back_populates="product_type")


class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    sku = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Decimal(10, 2), nullable=False)
    product_type_id = Column(Integer, ForeignKey('product_types.id'))
    supplier_id = Column(Integer, ForeignKey('suppliers.id'))
    is_bundle = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product_type = relationship("ProductType", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")
    inventory = relationship("Inventory", back_populates="product")
    bundle_components = relationship(
        "ProductBundle",
        foreign_keys="ProductBundle.bundle_product_id",
        back_populates="bundle_product"
    )
    component_of = relationship(
        "ProductBundle",
        foreign_keys="ProductBundle.component_product_id",
        back_populates="component_product"
    )
    sales = relationship("Sale", back_populates="product")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('price >= 0', name='check_price_non_negative'),
    )


class ProductBundle(Base):
    __tablename__ = 'product_bundles'
    
    id = Column(Integer, primary_key=True)
    bundle_product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    component_product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    
    # Relationships
    bundle_product = relationship("Product", foreign_keys=[bundle_product_id], back_populates="bundle_components")
    component_product = relationship("Product", foreign_keys=[component_product_id], back_populates="component_of")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('bundle_product_id', 'component_product_id', name='uq_bundle_component'),
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
        CheckConstraint('bundle_product_id != component_product_id', name='check_no_self_reference'),
    )


class Inventory(Base):
    __tablename__ = 'inventory'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    low_stock_threshold = Column(Integer)
    last_restocked_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="inventory")
    warehouse = relationship("Warehouse", back_populates="inventory")
    transactions = relationship("InventoryTransaction", back_populates="inventory")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('product_id', 'warehouse_id', name='uq_inventory_product_warehouse'),
        CheckConstraint('quantity >= 0', name='check_quantity_non_negative'),
    )


class InventoryTransaction(Base):
    __tablename__ = 'inventory_transactions'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id'), nullable=False)
    transaction_type = Column(String(50), nullable=False)  # 'sale', 'restock', 'adjustment', 'transfer'
    quantity_change = Column(Integer, nullable=False)
    quantity_before = Column(Integer, nullable=False)
    quantity_after = Column(Integer, nullable=False)
    reference_id = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer)  # User ID if you have users table
    
    # Relationships
    product = relationship("Product")
    warehouse = relationship("Warehouse")
    inventory = relationship("Inventory", back_populates="transactions")


class Sale(Base):
    __tablename__ = 'sales'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    sale_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    order_id = Column(String(100))
    customer_id = Column(Integer)
    
    # Relationships
    product = relationship("Product", back_populates="sales")
    warehouse = relationship("Warehouse")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_sale_quantity_positive'),
    )


class SupplierProduct(Base):
    __tablename__ = 'supplier_products'
    
    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    supplier_sku = Column(String(100))
    cost_price = Column(Decimal(10, 2))
    lead_time_days = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    supplier = relationship("Supplier", back_populates="supplier_products")
    product = relationship("Product")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('supplier_id', 'product_id', name='uq_supplier_product'),
    )

