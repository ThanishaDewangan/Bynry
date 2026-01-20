"""
Fixed implementation of the create_product endpoint.
Addresses all identified issues from Part 1.
"""

from flask import Flask, request, jsonify
from sqlalchemy import exc
from datetime import datetime

# Import database and models
# In a real application, these would be imported from your models file
# from models import db, Product, Inventory, Warehouse, Supplier, InventoryTransaction

app = Flask(__name__)

# Note: In production, db would be initialized elsewhere
# db = SQLAlchemy(app)

@app.route('/api/products', methods=['POST'])
def create_product():
    """
    Create a new product and initialize inventory.
    
    Expected JSON payload:
    {
        "name": "Product Name" (required),
        "sku": "SKU-001" (required, must be unique),
        "price": 99.99 (required, must be >= 0),
        "warehouse_id": 1 (required, must exist),
        "initial_quantity": 0 (required, must be >= 0),
        "description": "Optional description",
        "supplier_id": 1 (optional),
        "product_type_id": 1 (optional)
    }
    """
    try:
        # Validate request has JSON body
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.json
        if not data:
            return jsonify({"error": "Request body cannot be empty"}), 400
        
        # Validate required fields
        required_fields = ['name', 'sku', 'price', 'warehouse_id', 'initial_quantity']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
        
        # Validate data types and values
        # SKU validation
        sku = str(data['sku']).strip()
        if not sku:
            return jsonify({"error": "SKU cannot be empty"}), 400
        
        # Check SKU uniqueness
        existing_product = Product.query.filter_by(sku=sku).first()
        if existing_product:
            return jsonify({
                "error": f"Product with SKU '{sku}' already exists",
                "existing_product_id": existing_product.id
            }), 409  # Conflict status code
        
        # Price validation
        try:
            price = float(data['price'])
            if price < 0:
                return jsonify({"error": "Price must be non-negative"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Price must be a valid number"}), 400
        
        # Quantity validation
        try:
            initial_quantity = int(data['initial_quantity'])
            if initial_quantity < 0:
                return jsonify({"error": "Initial quantity must be non-negative"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Initial quantity must be a valid integer"}), 400
        
        # Warehouse validation
        warehouse_id = int(data['warehouse_id'])
        warehouse = Warehouse.query.get(warehouse_id)
        if not warehouse:
            return jsonify({
                "error": f"Warehouse with ID {warehouse_id} does not exist"
            }), 404
        
        # Name validation
        name = str(data['name']).strip()
        if not name:
            return jsonify({"error": "Product name cannot be empty"}), 400
        
        # Optional fields
        description = data.get('description', '').strip() if data.get('description') else None
        supplier_id = data.get('supplier_id')
        product_type_id = data.get('product_type_id')
        
        # Validate optional supplier_id if provided
        if supplier_id is not None:
            try:
                supplier_id = int(supplier_id)
                supplier = Supplier.query.get(supplier_id)
                if not supplier:
                    return jsonify({
                        "error": f"Supplier with ID {supplier_id} does not exist"
                    }), 404
            except (ValueError, TypeError):
                return jsonify({"error": "Supplier ID must be a valid integer"}), 400
        
        # Use a single transaction for atomicity
        try:
            # Create new product
            product = Product(
                name=name,
                sku=sku,
                price=price,
                description=description,
                supplier_id=supplier_id,
                product_type_id=product_type_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(product)
            db.session.flush()  # Flush to get product.id without committing
            
            # Create inventory record
            inventory = Inventory(
                product_id=product.id,
                warehouse_id=warehouse_id,
                quantity=initial_quantity,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(inventory)
            
            # Create inventory transaction record for audit trail
            transaction = InventoryTransaction(
                product_id=product.id,
                warehouse_id=warehouse_id,
                transaction_type='initial_stock',
                quantity_change=initial_quantity,
                quantity_before=0,
                quantity_after=initial_quantity,
                notes=f"Initial stock for new product {sku}",
                created_at=datetime.utcnow()
            )
            
            db.session.add(transaction)
            
            # Single commit for atomicity
            db.session.commit()
            
            # Return created product with proper status code
            return jsonify({
                "message": "Product created successfully",
                "product": {
                    "id": product.id,
                    "name": product.name,
                    "sku": product.sku,
                    "price": float(product.price),
                    "warehouse_id": warehouse_id,
                    "initial_quantity": initial_quantity,
                    "created_at": product.created_at.isoformat()
                }
            }), 201  # Created status code
            
        except exc.IntegrityError as e:
            db.session.rollback()
            # Handle any remaining integrity issues (e.g., race condition on SKU)
            if 'sku' in str(e).lower() or 'unique' in str(e).lower():
                return jsonify({
                    "error": f"Product with SKU '{sku}' already exists"
                }), 409
            return jsonify({
                "error": "Database integrity error",
                "details": str(e)
            }), 400
            
        except Exception as e:
            db.session.rollback()
            # Log the error (in production, use proper logging)
            print(f"Error creating product: {str(e)}")
            return jsonify({
                "error": "Failed to create product",
                "details": "Internal server error"
            }), 500
    
    except Exception as e:
        # Catch any unexpected errors
        db.session.rollback()
        print(f"Unexpected error: {str(e)}")
        return jsonify({
            "error": "An unexpected error occurred",
            "details": "Internal server error"
        }), 500

