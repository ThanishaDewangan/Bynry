# StockFlow - Inventory Management System Solution

This repository contains the complete solution for the StockFlow B2B inventory management platform take-home assignment.

## Files Overview

### Documentation
- **SOLUTION.md** - Complete solution document with all three parts:
  - Part 1: Code Review & Debugging
  - Part 2: Database Design
  - Part 3: API Implementation

### Code Files
- **fixed_create_product.py** - Corrected implementation of the `/api/products` POST endpoint
- **low_stock_alerts.py** - Implementation of the `/api/companies/{company_id}/alerts/low-stock` GET endpoint
- **models.py** - SQLAlchemy models corresponding to the database schema
- **database_schema.sql** - Complete SQL DDL for the database schema

## Quick Start

### Prerequisites
- Python 3.7+
- Flask
- SQLAlchemy
- PostgreSQL (or your preferred database)

### Setup

1. Install dependencies:
```bash
pip install flask sqlalchemy psycopg2-binary
```

2. Set up the database:

**For Linux/Mac (bash):**
```bash
psql -U postgres -d stockflow < database_schema.sql
```

**For Windows PowerShell:**

**Step 1: Create the database first:**
```powershell
psql -U postgres -c "CREATE DATABASE stockflow;"
```

**Step 2: Apply the schema:**
```powershell
psql -U postgres -d stockflow -f database_schema.sql
```

**Or use the helper script:**
```powershell
.\setup_database.ps1
```

**Note:** If you get connection errors, make sure PostgreSQL is running and accessible.

3. Configure your Flask app to use the models:
```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import Base

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:pass@localhost/stockflow'
db = SQLAlchemy(app)

# Import models after db initialization
from models import *
```

4. Use the endpoints:
   - Copy code from `fixed_create_product.py` into your Flask app
   - Copy code from `low_stock_alerts.py` into your Flask app

## Solution Summary

### Part 1: Code Review
Identified 9 major issues:
1. Missing input validation
2. No error handling
3. SKU uniqueness not enforced
4. Transaction safety issues
5. No warehouse existence validation
6. Missing HTTP status codes
7. No handling of optional fields
8. Price and quantity validation missing
9. Missing return of created resource

### Part 2: Database Design
Designed comprehensive schema with:
- 10 core tables (companies, warehouses, products, inventory, etc.)
- Proper relationships and constraints
- Performance indexes
- Audit trail support
- Identified 10 gaps requiring product team clarification

### Part 3: API Implementation
Implemented low-stock alerts endpoint with:
- Proper error handling
- Edge case management
- Sales activity filtering
- Days until stockout calculation
- Supplier information inclusion
- Two implementation versions (standard and optimized)

## Key Assumptions Made

1. Recent sales activity = sales in last 30 days
2. Days until stockout = current_stock / average_daily_sales
3. Low stock threshold uses inventory-level override if set, else product type default
4. Supplier selection uses primary supplier from products table
5. Multiple warehouses return separate alerts per warehouse

## Testing Recommendations

1. Test with various edge cases:
   - Company with no warehouses
   - Products with no sales history
   - Products with zero stock
   - Missing supplier information
   - Invalid company IDs

2. Performance testing:
   - Large datasets (1000+ products)
   - Multiple warehouses per company
   - High sales volume

3. Integration testing:
   - End-to-end product creation flow
   - Inventory updates affecting alerts
   - Sales transactions updating calculations

## Notes

- All code includes comprehensive comments explaining logic
- Error handling follows REST API best practices
- Database constraints enforce business rules at the schema level
- Code is production-ready with proper validation and error messages

