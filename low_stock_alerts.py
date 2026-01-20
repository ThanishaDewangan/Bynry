"""
Implementation of low-stock alerts endpoint for Part 3.
GET /api/companies/{company_id}/alerts/low-stock
"""

from flask import Flask, jsonify, request
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from decimal import Decimal

# Import database and models
# In a real application, these would be imported from your models file
# from models import db, Company, Warehouse, Product, Inventory, ProductType, Supplier, Sales

app = Flask(__name__)

# Note: In production, db would be initialized elsewhere
# db = SQLAlchemy(app)

# Configuration constants
RECENT_SALES_DAYS = 30  # Days to look back for "recent sales activity"
MIN_SALES_FOR_CALCULATION = 1  # Minimum sales needed to calculate days until stockout


@app.route('/api/companies/<int:company_id>/alerts/low-stock', methods=['GET'])
def get_low_stock_alerts(company_id):
    """
    Get low-stock alerts for a company.
    
    Query parameters (optional):
    - days: Number of days to look back for sales activity (default: 30)
    - include_no_sales: Include products with no recent sales (default: false)
    
    Returns:
    {
        "alerts": [
            {
                "product_id": int,
                "product_name": str,
                "sku": str,
                "warehouse_id": int,
                "warehouse_name": str,
                "current_stock": int,
                "threshold": int,
                "days_until_stockout": int | null,
                "supplier": {
                    "id": int,
                    "name": str,
                    "contact_email": str | null
                } | null
            }
        ],
        "total_alerts": int
    }
    """
    try:
        # Validate company exists
        company = Company.query.get(company_id)
        if not company:
            return jsonify({
                "error": f"Company with ID {company_id} does not exist"
            }), 404
        
        # Get query parameters
        days = request.args.get('days', type=int, default=RECENT_SALES_DAYS)
        include_no_sales = request.args.get('include_no_sales', type=bool, default=False)
        
        # Validate days parameter
        if days <= 0:
            return jsonify({
                "error": "Days parameter must be positive"
            }), 400
        
        # Calculate date threshold for recent sales
        sales_threshold_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all warehouses for this company
        warehouses = Warehouse.query.filter_by(company_id=company_id).all()
        if not warehouses:
            return jsonify({
                "alerts": [],
                "total_alerts": 0,
                "message": "No warehouses found for this company"
            }), 200
        
        warehouse_ids = [w.id for w in warehouses]
        
        # Query for low stock inventory
        # Join inventory with products, warehouses, product types, and suppliers
        query = db.session.query(
            Inventory,
            Product,
            Warehouse,
            ProductType,
            Supplier
        ).join(
            Product, Inventory.product_id == Product.id
        ).join(
            Warehouse, Inventory.warehouse_id == Warehouse.id
        ).outerjoin(
            ProductType, Product.product_type_id == ProductType.id
        ).outerjoin(
            Supplier, Product.supplier_id == Supplier.id
        ).filter(
            Inventory.warehouse_id.in_(warehouse_ids),
            # Low stock condition: quantity < threshold
            # Threshold is inventory.low_stock_threshold if set, else product_type.default_low_stock_threshold
            or_(
                and_(
                    Inventory.low_stock_threshold.isnot(None),
                    Inventory.quantity < Inventory.low_stock_threshold
                ),
                and_(
                    Inventory.low_stock_threshold.is_(None),
                    ProductType.default_low_stock_threshold.isnot(None),
                    Inventory.quantity < ProductType.default_low_stock_threshold
                ),
                # Fallback: if no threshold set, use default of 10
                and_(
                    Inventory.low_stock_threshold.is_(None),
                    ProductType.default_low_stock_threshold.is_(None),
                    Inventory.quantity < 10
                )
            )
        )
        
        low_stock_items = query.all()
        
        if not low_stock_items:
            return jsonify({
                "alerts": [],
                "total_alerts": 0
            }), 200
        
        # Get product IDs for sales activity check
        product_ids = [item[1].id for item in low_stock_items]
        
        # Calculate average daily sales for products with recent sales
        # Subquery: average daily sales per product per warehouse in last N days
        sales_subquery = db.session.query(
            Sales.product_id,
            Sales.warehouse_id,
            func.sum(Sales.quantity).label('total_sold'),
            func.count(func.distinct(func.date(Sales.sale_date))).label('days_with_sales')
        ).filter(
            Sales.sale_date >= sales_threshold_date,
            Sales.product_id.in_(product_ids)
        ).group_by(
            Sales.product_id,
            Sales.warehouse_id
        ).subquery()
        
        # Calculate days until stockout
        alerts = []
        
        for inventory, product, warehouse, product_type, supplier in low_stock_items:
            # Determine threshold
            threshold = (
                inventory.low_stock_threshold 
                if inventory.low_stock_threshold is not None
                else (
                    product_type.default_low_stock_threshold 
                    if product_type and product_type.default_low_stock_threshold is not None
                    else 10  # Default threshold
                )
            )
            
            # Check for recent sales activity
            recent_sales = db.session.query(sales_subquery).filter(
                sales_subquery.c.product_id == product.id,
                sales_subquery.c.warehouse_id == warehouse.id
            ).first()
            
            # Skip if no recent sales and include_no_sales is False
            if not recent_sales and not include_no_sales:
                continue
            
            # Calculate days until stockout
            days_until_stockout = None
            
            if recent_sales:
                total_sold = recent_sales.total_sold
                days_with_sales = recent_sales.days_with_sales
                
                if days_with_sales > 0:
                    # Average daily sales = total sold / days with sales
                    # But we want average over the full period, so divide by actual days
                    average_daily_sales = total_sold / days
                    
                    if average_daily_sales > 0:
                        # Days until stockout = current stock / average daily sales
                        days_until_stockout = int(inventory.quantity / average_daily_sales)
                    else:
                        days_until_stockout = None
                else:
                    days_until_stockout = None
            else:
                # No sales history - cannot calculate
                days_until_stockout = None
            
            # Build supplier information
            supplier_info = None
            if supplier:
                supplier_info = {
                    "id": supplier.id,
                    "name": supplier.name,
                    "contact_email": supplier.contact_email
                }
            
            # Build alert object
            alert = {
                "product_id": product.id,
                "product_name": product.name,
                "sku": product.sku,
                "warehouse_id": warehouse.id,
                "warehouse_name": warehouse.name,
                "current_stock": inventory.quantity,
                "threshold": threshold,
                "days_until_stockout": days_until_stockout,
                "supplier": supplier_info
            }
            
            alerts.append(alert)
        
        # Sort alerts by days_until_stockout (most urgent first)
        # Products with None (no sales) go to the end
        alerts.sort(key=lambda x: (
            x['days_until_stockout'] is None,
            x['days_until_stockout'] if x['days_until_stockout'] is not None else float('inf')
        ))
        
        return jsonify({
            "alerts": alerts,
            "total_alerts": len(alerts)
        }), 200
    
    except ValueError as e:
        return jsonify({
            "error": "Invalid parameter value",
            "details": str(e)
        }), 400
    
    except Exception as e:
        # Log error in production (use proper logging)
        print(f"Error fetching low stock alerts: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "error": "Failed to fetch low stock alerts",
            "details": "Internal server error"
        }), 500


# Alternative optimized version using a single query with subqueries
# This version is more efficient for large datasets
@app.route('/api/companies/<int:company_id>/alerts/low-stock-optimized', methods=['GET'])
def get_low_stock_alerts_optimized(company_id):
    """
    Optimized version using subqueries for better performance.
    Same functionality as above but with better query efficiency.
    """
    try:
        # Validate company exists
        company = Company.query.get(company_id)
        if not company:
            return jsonify({
                "error": f"Company with ID {company_id} does not exist"
            }), 404
        
        days = request.args.get('days', type=int, default=RECENT_SALES_DAYS)
        include_no_sales = request.args.get('include_no_sales', type=bool, default=False)
        
        if days <= 0:
            return jsonify({"error": "Days parameter must be positive"}), 400
        
        sales_threshold_date = datetime.utcnow() - timedelta(days=days)
        
        # Get warehouse IDs for company
        warehouse_ids = db.session.query(Warehouse.id).filter_by(
            company_id=company_id
        ).subquery()
        
        # Subquery for average daily sales
        avg_daily_sales_subq = db.session.query(
            Sales.product_id,
            Sales.warehouse_id,
            (func.sum(Sales.quantity) / days).label('avg_daily_sales')
        ).filter(
            Sales.sale_date >= sales_threshold_date
        ).group_by(
            Sales.product_id,
            Sales.warehouse_id
        ).subquery()
        
        # Main query with all joins and calculations
        query = db.session.query(
            Inventory.product_id,
            Inventory.warehouse_id,
            Inventory.quantity,
            Inventory.low_stock_threshold,
            Product.id.label('product_id'),
            Product.name.label('product_name'),
            Product.sku,
            Product.supplier_id,
            Warehouse.name.label('warehouse_name'),
            ProductType.default_low_stock_threshold,
            Supplier.id.label('supplier_id'),
            Supplier.name.label('supplier_name'),
            Supplier.contact_email.label('supplier_email'),
            avg_daily_sales_subq.c.avg_daily_sales
        ).select_from(Inventory).join(
            Product, Inventory.product_id == Product.id
        ).join(
            Warehouse, Inventory.warehouse_id == Warehouse.id
        ).outerjoin(
            ProductType, Product.product_type_id == ProductType.id
        ).outerjoin(
            Supplier, Product.supplier_id == Supplier.id
        ).outerjoin(
            avg_daily_sales_subq,
            and_(
                avg_daily_sales_subq.c.product_id == Inventory.product_id,
                avg_daily_sales_subq.c.warehouse_id == Inventory.warehouse_id
            )
        ).filter(
            Inventory.warehouse_id.in_(db.session.query(warehouse_ids.c.id)),
            # Low stock condition
            func.coalesce(
                Inventory.low_stock_threshold,
                ProductType.default_low_stock_threshold,
                10
            ) > Inventory.quantity
        )
        
        # Apply filter for recent sales if needed
        if not include_no_sales:
            query = query.filter(avg_daily_sales_subq.c.avg_daily_sales.isnot(None))
        
        results = query.all()
        
        alerts = []
        for row in results:
            threshold = (
                row.low_stock_threshold 
                if row.low_stock_threshold is not None
                else (
                    row.default_low_stock_threshold 
                    if row.default_low_stock_threshold is not None
                    else 10
                )
            )
            
            days_until_stockout = None
            if row.avg_daily_sales and row.avg_daily_sales > 0:
                days_until_stockout = int(row.quantity / row.avg_daily_sales)
            
            supplier_info = None
            if row.supplier_id:
                supplier_info = {
                    "id": row.supplier_id,
                    "name": row.supplier_name,
                    "contact_email": row.supplier_email
                }
            
            alerts.append({
                "product_id": row.product_id,
                "product_name": row.product_name,
                "sku": row.sku,
                "warehouse_id": row.warehouse_id,
                "warehouse_name": row.warehouse_name,
                "current_stock": row.quantity,
                "threshold": threshold,
                "days_until_stockout": days_until_stockout,
                "supplier": supplier_info
            })
        
        # Sort by urgency
        alerts.sort(key=lambda x: (
            x['days_until_stockout'] is None,
            x['days_until_stockout'] if x['days_until_stockout'] is not None else float('inf')
        ))
        
        return jsonify({
            "alerts": alerts,
            "total_alerts": len(alerts)
        }), 200
    
    except Exception as e:
        print(f"Error fetching low stock alerts: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "error": "Failed to fetch low stock alerts",
            "details": "Internal server error"
        }), 500

