from flask import Blueprint, request, jsonify, send_file, send_from_directory, current_app, abort
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from config import db
from werkzeug.security import check_password_hash, generate_password_hash
import re
import os
import functools
import csv
import io
import datetime
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from ai.process import process_image

api_routes = Blueprint("api_routes", __name__)

# ----- Permission -----

# Define permission levels
PERMISSIONS = {
    "admin": [
        "view_dashboard",
        "view_inventory",
        "add_item",
        "edit_item",
        "delete_item",
        "view_categories",
        "add_category",
        "edit_category",
        "delete_category",
        "view_transactions",
        "add_transaction",
        "view_users",
        "add_user",
        "edit_user",
        "delete_user",
        "view_reports",
        "generate_report",
        "use_ai_detection",
    ],
    "staff": [
        "view_dashboard",
        "view_inventory",
        "add_item",
        "edit_item",
        "view_categories",
        "view_transactions",
        "add_transaction",
        "view_reports",
        "generate_report",
        "use_ai_detection",
    ],
    "viewer": [
        "view_dashboard",
        "view_inventory",
        "view_categories",
        "view_transactions",
        "view_reports",
    ],
}


def permission_required(permission):
    def decorator(func):
        @functools.wraps(func)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()

            if "role" not in claims:
                return jsonify({"error": "Invalid token"}), 422

            role = claims["role"]

            if role not in PERMISSIONS or permission not in PERMISSIONS[role]:
                return (
                    jsonify(
                        {
                            "error": "You don't have permission to perform this action",
                            "required_permission": permission,
                        }
                    ),
                    403,
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator


def role_required(roles):
    def decorator(func):
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()

            if "role" not in claims:
                return jsonify({"error": "Invalid token"}), 422

            if claims["role"] not in roles:
                return jsonify({"error": "Insufficient permissions"}), 403

            return func(*args, **kwargs)

        wrapper.__name__ = f"{func.__name__}_protected"
        return wrapper

    return decorator


def validate_password(password):
    """Check if the password meets the required criteria."""
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return "Password must contain at least one digit."
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return "Password must contain at least one special character."
    return None


# ----- Permissions API -----


@api_routes.route("/api/permissions", methods=["GET"])
@jwt_required()
def get_permissions():
    claims = get_jwt()

    if "role" not in claims:
        return jsonify({"error": "Invalid token"}), 422

    role = claims["role"]

    if role not in PERMISSIONS:
        return jsonify({"error": "Invalid role"}), 400

    return jsonify({"role": role, "permissions": PERMISSIONS[role]}), 200


# ----- AI & Image Processing Routes -----


# AI object detection endpoint
@api_routes.route("/api/detect-objects", methods=["POST"])
@role_required(["admin", "staff"])
def detect_objects():
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:5173")
        response.headers.add(
            "Access-Control-Allow-Headers", "Content-Type,Authorization"
        )
        response.headers.add("Access-Control-Allow-Methods", "POST,OPTIONS")
        return response

    return process_image()


# Serve result images
@api_routes.route("/api/images/<filename>", methods=["GET"])
def serve_image(filename):

    results_dir = os.path.join(os.getcwd(), "results")

    os.makedirs(results_dir, exist_ok=True)
    
    file_path = os.path.join(results_dir, filename)

    print(f"Looking for image: {filename}")
    print(f"Full path: {file_path}")
    print(f"File exists: {os.path.exists(file_path)}")
    
    if os.path.exists(results_dir):
        print(f"Files in results directory: {os.listdir(results_dir)}")

    if not os.path.exists(file_path):
        print(f"Image not found: {filename}")
        abort(404)
    
    try:
        return send_from_directory(results_dir, filename)
    except Exception as e:
        print(f"Error serving image: {e}")
        abort(404)


# ----- Item Routes -----


# Public endpoint for items (read-only)
@api_routes.route("/api/items", methods=["GET"])
def get_items():
    try:
        cursor = db.connection.cursor()
        cursor.execute("SELECT * FROM items")
        items = cursor.fetchall()

        results = [
            {
                "item_id": item[0],
                "name": item[1],
                "category_id": item[2],
                "quantity": item[3],
                "image_path": item[4],
            }
            for item in items
        ]

        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Get a single item by ID
@api_routes.route("/api/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    try:
        cursor = db.connection.cursor()
        cursor.execute("SELECT * FROM items WHERE item_id = %s", (item_id,))
        item = cursor.fetchone()

        if not item:
            return jsonify({"error": "Item not found"}), 404

        result = {
            "item_id": item[0],
            "name": item[1],
            "category_id": item[2],
            "quantity": item[3],
            "image_path": item[4],
        }

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Add a new item (admin and staff)
@api_routes.route("/api/items", methods=["POST"])
@role_required(["admin", "staff"])
def add_item():
    try:
        data = request.json

        if not data.get("name"):
            return jsonify({"error": "Item name is required"}), 400
        if not data.get("category_id"):
            return jsonify({"error": "Category is required"}), 400
        if "quantity" not in data:
            return jsonify({"error": "Quantity is required"}), 400

        cursor = db.connection.cursor()
        cursor.execute(
            "INSERT INTO items (name, category_id, quantity, image_path) VALUES (%s, %s, %s, %s)",
            (
                data["name"],
                data["category_id"],
                data["quantity"],
                data.get("image_path"),
            ),
        )

        item_id = cursor.lastrowid
        db.connection.commit()

        return jsonify({"message": "Item added successfully", "item_id": item_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Update an item (admin and staff)
@api_routes.route("/api/items/<int:item_id>", methods=["PUT"])
@role_required(["admin", "staff"])
def update_item(item_id):
    try:
        data = request.get_json()

        cursor = db.connection.cursor()
        cursor.execute("SELECT * FROM items WHERE item_id = %s", (item_id,))
        current_item = cursor.fetchone()

        if not current_item:
            return jsonify({"error": "Item not found"}), 404

        cursor.execute(
            "UPDATE items SET name = %s, category_id = %s, quantity = %s, image_path = %s WHERE item_id = %s",
            (
                data["name"],
                data["category_id"],
                data["quantity"],
                data.get("image_path"),
                item_id,
            ),
        )
        db.connection.commit()
        return jsonify({"message": "Item updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Delete an item (admin and staff)
@api_routes.route("/api/items/<int:item_id>", methods=["DELETE"])
@role_required(["admin", "staff"])
def delete_item(item_id):
    try:
        cursor = db.connection.cursor()

        # Check if the item exists
        cursor.execute("SELECT * FROM items WHERE item_id = %s", (item_id,))
        item = cursor.fetchone()
        if not item:
            return jsonify({"error": "Item not found"}), 404

        cursor.execute("SELECT * FROM transactions WHERE item_id = %s", (item_id,))
        transaction = cursor.fetchone()
        if transaction:
            return (
                jsonify(
                    {"error": "Cannot delete item, it is referenced in transactions"}
                ),
                400,
            )

        # Delete the item
        cursor.execute("DELETE FROM items WHERE item_id = %s", (item_id,))
        db.connection.commit()
        return jsonify({"message": "Item deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_routes.route("/api/object-mappings", methods=["GET"])
@role_required(["admin", "staff"])
def get_mappings():
    try:
        from models import get_object_mappings

        mappings = get_object_mappings()
        return jsonify(mappings), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_routes.route("/api/object-mappings", methods=["POST"])
@role_required(["admin", "staff"])
def add_mapping():
    try:
        data = request.json
        if not data or "object_name" not in data or "category_id" not in data:
            return jsonify({"error": "Missing required fields"}), 400

        from models import add_object_mapping

        success = add_object_mapping(data["object_name"], data["category_id"])

        if success:
            return jsonify({"message": "Mapping added successfully"}), 201
        else:
            return jsonify({"error": "Failed to add mapping"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----- Category Routes -----


# Public endpoint for categories (read-only)
@api_routes.route("/api/categories", methods=["GET"])
def get_categories():
    try:
        cursor = db.connection.cursor()
        cursor.execute("SELECT * FROM categories")
        categories = cursor.fetchall()

        results = [
            {"category_id": cat[0], "category_name": cat[1]} for cat in categories
        ]
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Add categories (admin)
@api_routes.route("/api/categories", methods=["POST"])
@role_required(["admin"])
def add_category():
    try:
        data = request.json
        if "category_name" not in data:
            return jsonify({"error": "Missing category_name"}), 400

        cursor = db.connection.cursor()
        cursor.execute(
            "INSERT INTO categories (category_name) VALUES (%s)",
            (data["category_name"],),
        )
        category_id = cursor.lastrowid
        db.connection.commit()

        return (
            jsonify(
                {"category_id": category_id, "category_name": data["category_name"]}
            ),
            201,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Update categories (admin)
@api_routes.route("/api/categories/<int:category_id>", methods=["PUT"])
@role_required(["admin"])
def update_category(category_id):
    try:
        data = request.json
        if "category_name" not in data:
            return jsonify({"error": "Missing category_name"}), 400

        cursor = db.connection.cursor()
        cursor.execute(
            "UPDATE categories SET category_name = %s WHERE category_id = %s",
            (data["category_name"], category_id),
        )
        db.connection.commit()
        return jsonify({"message": "Category updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Delete categories (admin)
@api_routes.route("/api/categories/<int:category_id>", methods=["DELETE"])
@role_required(["admin"])
def delete_category(category_id):
    try:
        cursor = db.connection.cursor()

        # Check if category is used in any items
        cursor.execute(
            "SELECT COUNT(*) FROM items WHERE category_id = %s", (category_id,)
        )
        item_count = cursor.fetchone()[0]

        if item_count > 0:
            return (
                jsonify(
                    {
                        "error": f"Cannot delete category, it is used by {item_count} items"
                    }
                ),
                400,
            )

        cursor.execute("DELETE FROM categories WHERE category_id = %s", (category_id,))
        db.connection.commit()
        return jsonify({"message": "Category deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----- User Routes -----


# Get all users (admin only)
@api_routes.route("/api/users", methods=["GET"])
@role_required(["admin"])
def get_users():
    try:
        cursor = db.connection.cursor()
        cursor.execute("SELECT user_id, username, role FROM users")
        users = cursor.fetchall()

        results = [
            {"user_id": user[0], "username": user[1], "role": user[2]} for user in users
        ]

        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Add a new user (admin only)
@api_routes.route("/api/users", methods=["POST"])
@role_required(["admin"])
def add_user():
    try:
        data = request.json

        if not data.get("username"):
            return jsonify({"errors": {"username": ["Username is required."]}})
        if not data.get("password"):
            return jsonify({"errors": {"password": ["Password is required."]}})
        if not data.get("role"):
            return jsonify({"errors": {"role": ["Role is required."]}})

        validation_error = validate_password(data["password"])
        if validation_error:
            return jsonify({"errors": {"password": [validation_error]}}), 422

        hashed_password = generate_password_hash(data["password"])
        cursor = db.connection.cursor()
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            (data["username"], hashed_password, data["role"]),
        )
        db.connection.commit()

        return jsonify({"message": "User created successfully."}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Update a user (admin)
@api_routes.route("/api/users/<int:user_id>", methods=["PUT"])
@role_required(["admin"])
def update_user(user_id):
    try:
        data = request.json
        updates = []
        params = []

        if "username" in data:
            updates.append("username = %s")
            params.append(data["username"])

        if "password" in data:
            validation_error = validate_password(data["password"])
            if validation_error:
                return jsonify({"errors": {"password": validation_error}}), 422

            updates.append("password = %s")
            params.append(generate_password_hash(data["password"]))

        if "role" in data:
            updates.append("role = %s")
            params.append(data["role"])

        if updates:
            query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = %s"
            params.append(user_id)
            cursor = db.connection.cursor()
            cursor.execute(query, tuple(params))
            db.connection.commit()

        return jsonify({"message": "User updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_routes.route("/api/users/<int:user_id>/password", methods=["PUT"])
@jwt_required()
def update_user_password(user_id):
    try:
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        current_user_role = claims.get("role", "")
        
        if int(current_user_id) != user_id and current_user_role != "admin":
            return jsonify({"error": "You can only update your own password"}), 403
        
        data = request.json
        if not data or "currentPassword" not in data or "newPassword" not in data:
            return jsonify({"error": "Missing required fields"}), 400

        cursor = db.connection.cursor()
        cursor.execute("SELECT password FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        current_password_hash = user[0]
        
        if not check_password_hash(current_password_hash, data["currentPassword"]):
            return jsonify({"error": "Current password is incorrect"}), 401

        validation_error = validate_password(data["newPassword"])
        if validation_error:
            return jsonify({"error": validation_error}), 422

        new_password_hash = generate_password_hash(data["newPassword"])
        cursor.execute(
            "UPDATE users SET password = %s WHERE user_id = %s",
            (new_password_hash, user_id)
        )
        db.connection.commit()
        
        return jsonify({"message": "Password updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----- Transaction Routes -----

# Get all transactions
@api_routes.route("/api/transactions", methods=["GET"])
@role_required(["admin", "staff"])
def get_transactions():
    try:
        cursor = db.connection.cursor()
        cursor.execute(
            """
            SELECT t.transaction_id, t.item_id, t.user_id, t.transaction_type, 
                   t.quantity_change, t.transaction_date, t.notes, u.username
            FROM transactions t
            JOIN users u ON t.user_id = u.user_id
            ORDER BY t.transaction_date DESC
        """
        )
        transactions = cursor.fetchall()

        results = [
            {
                "transaction_id": t[0],
                "item_id": t[1],
                "user_id": t[2],
                "transaction_type": t[3],
                "quantity_change": t[4],
                "transaction_date": str(t[5]),
                "notes": t[6],
                "username": t[7],
            }
            for t in transactions
        ]

        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Add a new transaction
@api_routes.route("/api/transactions", methods=["POST"])
@role_required(["admin", "staff"])
def add_transaction():
    try:
        data = request.json
        user_id = get_jwt_identity()

        if not data or not all(
            k in data for k in ["item_id", "transaction_type", "quantity_change"]
        ):
            return jsonify({"error": "Missing required fields"}), 400

        if data["transaction_type"] not in ["in", "out"]:
            return (
                jsonify({"error": "Invalid transaction type. Must be 'in' or 'out'"}),
                400,
            )

        try:
            quantity = int(data["quantity_change"])
            if quantity <= 0:
                return jsonify({"error": "Quantity must be positive"}), 400
        except ValueError:
            return jsonify({"error": "Quantity must be a number"}), 400

        cursor = db.connection.cursor() if hasattr(db, 'connection') else db.cursor()

        cursor.execute(
            "SELECT quantity FROM items WHERE item_id = %s", (data["item_id"],)
        )
        item = cursor.fetchone()

        if not item:
            return jsonify({"error": "Item not found"}), 404

        current_quantity = item[0]

        if data["transaction_type"] == "out" and quantity > current_quantity:
            return (
                jsonify(
                    {"error": f"Not enough stock. Current quantity: {current_quantity}"}
                ),
                400,
            )

        new_quantity = (
            current_quantity + quantity
            if data["transaction_type"] == "in"
            else current_quantity - quantity
        )

        try:
            cursor.execute(
                """
                INSERT INTO transactions 
                (item_id, user_id, transaction_type, quantity_change, notes) 
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    data["item_id"],
                    user_id,
                    data["transaction_type"],
                    quantity,
                    data.get("notes"),
                ),
            )

            cursor.execute(
                "UPDATE items SET quantity = %s WHERE item_id = %s",
                (new_quantity, data["item_id"]),
            )

            if hasattr(db, 'connection') and hasattr(db.connection, 'commit'):
                db.connection.commit()

            return jsonify({"message": "Transaction added successfully"}), 201
            
        except Exception as e:
            if hasattr(db, 'connection') and hasattr(db.connection, 'rollback'):
                db.connection.rollback()
            raise e

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Get transaction by ID
@api_routes.route("/api/transactions/<int:transaction_id>", methods=["GET"])
@role_required(["admin", "staff"])
def get_transaction(transaction_id):
    try:
        cursor = db.connection.cursor()
        cursor.execute(
            """
            SELECT t.transaction_id, t.item_id, t.user_id, t.transaction_type, 
                   t.quantity_change, t.transaction_date, t.notes, u.username,
                   i.name as item_name
            FROM transactions t
            JOIN users u ON t.user_id = u.user_id
            JOIN items i ON t.item_id = i.item_id
            WHERE t.transaction_id = %s
        """,
            (transaction_id,),
        )

        transaction = cursor.fetchone()

        if not transaction:
            return jsonify({"error": "Transaction not found"}), 404

        result = {
            "transaction_id": transaction[0],
            "item_id": transaction[1],
            "user_id": transaction[2],
            "transaction_type": transaction[3],
            "quantity_change": transaction[4],
            "transaction_date": str(transaction[5]),
            "notes": transaction[6],
            "username": transaction[7],
            "item_name": transaction[8],
        }

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----- Report Routes -----


@api_routes.route("/api/generate-report", methods=["GET"])
@permission_required("generate_report")
def generate_report():
    try:
        report_type = request.args.get("reportType", "inventory")
        start_date = request.args.get("startDate")
        end_date = request.args.get("endDate")

        if start_date:
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start_date = datetime.datetime.now() - datetime.timedelta(days=30)

        if end_date:
            end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end_date = datetime.datetime.now()

        end_date = end_date + datetime.timedelta(days=1)

        if report_type == "inventory":
            return generate_inventory_report()
        elif report_type == "category":
            category_id = request.args.get("categoryId")
            return generate_category_report(category_id)
        elif report_type == "transaction":
            transaction_type = request.args.get("transactionType")
            return generate_transaction_report(start_date, end_date, transaction_type)
        elif report_type == "low-stock":
            return generate_low_stock_report()
        else:
            return jsonify({"error": "Invalid report type"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_routes.route("/api/download-report", methods=["GET"])
@permission_required("generate_report")
def download_report():
    try:
        report_type = request.args.get("reportType", "inventory")
        format_type = request.args.get("format", "pdf")

        if report_type == "inventory":
            response, _ = generate_inventory_report()
        elif report_type == "category":
            category_id = request.args.get("categoryId")
            response, _ = generate_category_report(category_id)
        elif report_type == "transaction":
            start_date = request.args.get("startDate")
            end_date = request.args.get("endDate")
            transaction_type = request.args.get("transactionType")

            if start_date:
                start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            else:
                start_date = datetime.datetime.now() - datetime.timedelta(days=30)

            if end_date:
                end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            else:
                end_date = datetime.datetime.now()

            response, _ = generate_transaction_report(
                start_date, end_date, transaction_type
            )
        elif report_type == "low-stock":
            response, _ = generate_low_stock_report()
        else:
            return jsonify({"error": "Invalid report type"}), 400

        if format_type == "pdf":
            return generate_pdf_report(response.json, report_type)
        elif format_type == "excel":
            return generate_excel_report(response.json, report_type)
        elif format_type == "csv":
            return generate_csv_report(response.json, report_type)
        else:
            return jsonify({"error": "Invalid format type"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def generate_inventory_report():
    """Generate inventory status report"""
    cursor = db.connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) as total_items, 
               SUM(quantity) as total_quantity,
               COUNT(CASE WHEN quantity <= 10 THEN 1 END) as low_stock_count
        FROM items
    """
    )
    summary_data = cursor.fetchone()

    cursor.execute(
        """
        SELECT c.category_name, COUNT(i.item_id) as item_count, SUM(i.quantity) as total_quantity
        FROM items i
        JOIN categories c ON i.category_id = c.category_id
        GROUP BY c.category_id, c.category_name
        ORDER BY item_count DESC
    """
    )
    category_data = cursor.fetchall()

    cursor.execute(
        """
        SELECT i.name, i.quantity, c.category_name
        FROM items i
        JOIN categories c ON i.category_id = c.category_id
        ORDER BY i.quantity DESC
    """
    )
    items_data = cursor.fetchall()

    chart_labels = [cat[0] for cat in category_data]
    chart_values = [cat[2] if cat[2] is not None else 0 for cat in category_data]

    response = {
        "summary": [
            {"title": "Total Items", "value": summary_data[0]},
            {
                "title": "Total Quantity",
                "value": summary_data[1] if summary_data[1] is not None else 0,
            },
            {"title": "Low Stock Items", "value": summary_data[2]},
        ],
        "chartData": {
            "type": "bar",
            "labels": chart_labels,
            "datasets": [
                {
                    "label": "Quantity by Category",
                    "data": chart_values,
                    "backgroundColor": "rgba(124, 77, 255, 0.7)",
                    "borderColor": "#7c4dff",
                    "borderWidth": 1,
                }
            ],
        },
        "headers": [
            {"title": "Item Name", "key": "name"},
            {"title": "Category", "key": "category"},
            {"title": "Quantity", "key": "quantity"},
        ],
        "items": [
            {"name": item[0], "category": item[2], "quantity": item[1]}
            for item in items_data
        ],
    }

    return jsonify(response), 200


def generate_category_report(category_id=None):
    """Generate category analysis report"""
    cursor = db.connection.cursor()

    if category_id:
        cursor.execute(
            """
            SELECT c.category_name, COUNT(i.item_id) as item_count, 
                   SUM(i.quantity) as total_quantity,
                   AVG(i.quantity) as avg_quantity
            FROM categories c
            LEFT JOIN items i ON c.category_id = i.category_id
            WHERE c.category_id = %s
            GROUP BY c.category_id, c.category_name
        """,
            (category_id,),
        )
        category_info = cursor.fetchone()

        if not category_info:
            return jsonify({"error": "Category not found"}), 404

        cursor.execute(
            """
            SELECT i.name, i.quantity
            FROM items i
            WHERE i.category_id = %s
            ORDER BY i.quantity DESC
        """,
            (category_id,),
        )
        items_data = cursor.fetchall()

        quantities = [item[1] for item in items_data]
        item_names = [item[0] for item in items_data]

        response = {
            "summary": [
                {"title": "Total Items", "value": category_info[1] or 0},
                {"title": "Total Quantity", "value": category_info[2] or 0},
                {"title": "Average Quantity", "value": round(category_info[3] or 0, 2)},
            ],
            "chartData": {
                "type": "bar",
                "labels": item_names,
                "datasets": [
                    {
                        "label": f"Quantity per Item in {category_info[0]}",
                        "data": quantities,
                        "backgroundColor": "rgba(76, 175, 80, 0.7)",
                        "borderColor": "#4caf50",
                        "borderWidth": 1,
                    }
                ],
            },
            "headers": [
                {"title": "Item Name", "key": "name"},
                {"title": "Quantity", "key": "quantity"},
            ],
            "items": [{"name": item[0], "quantity": item[1]} for item in items_data],
        }
    else:
        cursor.execute(
            """
            SELECT c.category_name, COUNT(i.item_id) as item_count, 
                   SUM(i.quantity) as total_quantity
            FROM categories c
            LEFT JOIN items i ON c.category_id = i.category_id
            GROUP BY c.category_id, c.category_name
            ORDER BY item_count DESC
        """
        )
        categories_data = cursor.fetchall()

        chart_labels = [cat[0] for cat in categories_data]
        chart_items = [cat[1] for cat in categories_data]
        chart_quantities = [cat[2] or 0 for cat in categories_data]

        response = {
            "summary": [
                {"title": "Total Categories", "value": len(categories_data)},
                {"title": "Total Items", "value": sum(chart_items)},
                {"title": "Total Quantity", "value": sum(chart_quantities)},
            ],
            "chartData": {
                "type": "pie",
                "labels": chart_labels,
                "datasets": [
                    {
                        "label": "Items per Category",
                        "data": chart_items,
                        "backgroundColor": [
                            "rgba(124, 77, 255, 0.7)",
                            "rgba(76, 175, 80, 0.7)",
                            "rgba(33, 150, 243, 0.7)",
                            "rgba(255, 82, 82, 0.7)",
                            "rgba(255, 193, 7, 0.7)",
                            "rgba(0, 188, 212, 0.7)",
                        ],
                    }
                ],
            },
            "headers": [
                {"title": "Category", "key": "category"},
                {"title": "Items Count", "key": "items"},
                {"title": "Total Quantity", "key": "quantity"},
            ],
            "items": [
                {"category": cat[0], "items": cat[1], "quantity": cat[2] or 0}
                for cat in categories_data
            ],
        }

    return jsonify(response), 200


def generate_transaction_report(start_date, end_date, transaction_type=None):
    """Generate transaction history report"""
    cursor = db.connection.cursor()

    params = [start_date, end_date]
    type_filter = ""

    if transaction_type:
        type_filter = "AND t.transaction_type = %s"
        params.append(transaction_type)

    cursor.execute(
        f"""
        SELECT COUNT(*) as total_transactions,
               SUM(CASE WHEN t.transaction_type = 'in' THEN 1 ELSE 0 END) as stock_in_count,
               SUM(CASE WHEN t.transaction_type = 'out' THEN 1 ELSE 0 END) as stock_out_count,
               SUM(CASE WHEN t.transaction_type = 'in' THEN t.quantity_change ELSE 0 END) as total_in,
               SUM(CASE WHEN t.transaction_type = 'out' THEN t.quantity_change ELSE 0 END) as total_out
        FROM transactions t
        WHERE t.transaction_date BETWEEN %s AND %s
        {type_filter}
    """,
        tuple(params),
    )

    summary_data = cursor.fetchone()

    query = f"""
        SELECT DATE(t.transaction_date) as date,
               SUM(CASE WHEN t.transaction_type = 'in' THEN t.quantity_change ELSE 0 END) as in_quantity,
               SUM(CASE WHEN t.transaction_type = 'out' THEN t.quantity_change ELSE 0 END) as out_quantity
        FROM transactions t
        WHERE t.transaction_date BETWEEN %s AND %s
        {type_filter}
        GROUP BY DATE(t.transaction_date)
        ORDER BY date
    """

    cursor.execute(query, tuple(params))
    date_data = cursor.fetchall()

    query = f"""
        SELECT t.transaction_id, i.name as item_name, u.username, 
               t.transaction_type, t.quantity_change, t.transaction_date, t.notes
        FROM transactions t
        JOIN items i ON t.item_id = i.item_id
        JOIN users u ON t.user_id = u.user_id
        WHERE t.transaction_date BETWEEN %s AND %s
        {type_filter}
        ORDER BY t.transaction_date DESC
        LIMIT 100
    """

    cursor.execute(query, tuple(params))
    transactions = cursor.fetchall()

    chart_labels = [str(date[0]) for date in date_data]
    in_data = [date[1] for date in date_data]
    out_data = [date[2] for date in date_data]

    response = {
        "summary": [
            {"title": "Total Transactions", "value": summary_data[0]},
            {"title": "Stock In", "value": summary_data[1]},
            {"title": "Stock Out", "value": summary_data[2]},
        ],
        "chartData": {
            "type": "line",
            "labels": chart_labels,
            "datasets": [
                {
                    "label": "Stock In",
                    "data": in_data,
                    "backgroundColor": "rgba(76, 175, 80, 0.2)",
                    "borderColor": "#4caf50",
                    "borderWidth": 2,
                    "tension": 0.3,
                },
                {
                    "label": "Stock Out",
                    "data": out_data,
                    "backgroundColor": "rgba(255, 82, 82, 0.2)",
                    "borderColor": "#ff5252",
                    "borderWidth": 2,
                    "tension": 0.3,
                },
            ],
        },
        "headers": [
            {"title": "ID", "key": "id"},
            {"title": "Item", "key": "item"},
            {"title": "Type", "key": "type"},
            {"title": "Quantity", "key": "quantity"},
            {"title": "Date", "key": "date"},
            {"title": "User", "key": "user"},
        ],
        "items": [
            {
                "id": t[0],
                "item": t[1],
                "user": t[2],
                "type": "Stock In" if t[3] == "in" else "Stock Out",
                "quantity": t[4],
                "date": t[5].strftime("%Y-%m-%d %H:%M:%S"),
                "notes": t[6],
            }
            for t in transactions
        ],
    }

    return jsonify(response), 200


def generate_low_stock_report():
    """Generate low stock items report"""
    cursor = db.connection.cursor()

    cursor.execute(
        """
        SELECT i.item_id, i.name, i.quantity, c.category_name,
               (SELECT MAX(t.transaction_date) FROM transactions t WHERE t.item_id = i.item_id) as last_updated
        FROM items i
        JOIN categories c ON i.category_id = c.category_id
        WHERE i.quantity <= 10
        ORDER BY i.quantity ASC
    """
    )
    items_data = cursor.fetchall()

    total_low_stock = len(items_data)
    critical_stock = len([item for item in items_data if item[2] <= 5])

    items = [item[1] for item in items_data]
    quantities = [item[2] for item in items_data]

    response = {
        "summary": [
            {"title": "Low Stock Items", "value": total_low_stock},
            {"title": "Critical Stock", "value": critical_stock},
            {
                "title": "Average Quantity",
                "value": (
                    round(sum(quantities) / len(quantities), 2) if quantities else 0
                ),
            },
        ],
        "chartData": {
            "type": "bar",
            "labels": items,
            "datasets": [
                {
                    "label": "Quantity",
                    "data": quantities,
                    "backgroundColor": [
                        "rgba(255, 82, 82, 0.7)" if q <= 5 else "rgba(255, 193, 7, 0.7)"
                        for q in quantities
                    ],
                    "borderColor": [
                        "#ff5252" if q <= 5 else "#ffc107" for q in quantities
                    ],
                    "borderWidth": 1,
                }
            ],
        },
        "headers": [
            {"title": "Item Name", "key": "name"},
            {"title": "Category", "key": "category"},
            {"title": "Quantity", "key": "quantity"},
            {"title": "Last Updated", "key": "lastUpdated"},
        ],
        "items": [
            {
                "id": item[0],
                "name": item[1],
                "quantity": item[2],
                "category": item[3],
                "lastUpdated": (
                    item[4].strftime("%Y-%m-%d %H:%M:%S") if item[4] else "N/A"
                ),
            }
            for item in items_data
        ],
    }

    return jsonify(response), 200


def generate_pdf_report(data, report_type):
    """Generate PDF report"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    subtitle_style = styles["Heading2"]
    normal_style = styles["Normal"]

    title = "Inventory System Report"
    if report_type == "inventory":
        title = "Inventory Status Report"
    elif report_type == "category":
        title = "Category Analysis Report"
    elif report_type == "transaction":
        title = "Transaction History Report"
    elif report_type == "low-stock":
        title = "Low Stock Alert Report"

    elements.append(Paragraph(title, title_style))
    elements.append(
        Paragraph(
            f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            normal_style,
        )
    )

    elements.append(Paragraph("Summary", subtitle_style))
    summary_data = []
    for item in data["summary"]:
        summary_data.append([item["title"], str(item["value"])])

    summary_table = Table(summary_data, colWidths=[300, 200])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), "#f5f5f5"),
                ("TEXTCOLOR", (0, 0), (-1, -1), "#333333"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("GRID", (0, 0), (-1, -1), 1, "#888888"),
            ]
        )
    )
    elements.append(summary_table)

    if "items" in data and data["items"]:
        elements.append(Paragraph("Details", subtitle_style))

        header_row = [h["title"] for h in data["headers"]]
        table_data = [header_row]

        for item in data["items"]:
            row = []
            for h in data["headers"]:
                key = h["key"]
                if key in item:
                    row.append(str(item[key]))
                else:
                    row.append("")
            table_data.append(row)

        details_table = Table(table_data[:101], colWidths=[120] * len(header_row))
        details_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), "#7c4dff"),
                    ("TEXTCOLOR", (0, 0), (-1, 0), "#ffffff"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), "#f9f9f9"),
                    ("GRID", (0, 0), (-1, -1), 1, "#888888"),
                ]
            )
        )
        elements.append(details_table)

        if len(data["items"]) > 100:
            elements.append(
                Paragraph(f"Showing 100 of {len(data['items'])} items", normal_style)
            )

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{report_type}-report-{datetime.datetime.now().strftime('%Y%m%d')}.pdf",
        mimetype="application/pdf",
    )


def generate_excel_report(data, report_type):
    """Generate Excel report"""
    buffer = io.BytesIO()

    writer = pd.ExcelWriter(buffer, engine="xlsxwriter")

    summary_df = pd.DataFrame(
        [{"Metric": item["title"], "Value": item["value"]} for item in data["summary"]]
    )

    if "items" in data and data["items"]:
        details_df = pd.DataFrame(data["items"])
    else:
        details_df = pd.DataFrame()

    summary_df.to_excel(writer, sheet_name="Summary", index=False)

    if not details_df.empty:
        details_df.to_excel(writer, sheet_name="Details", index=False)

    writer.close()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{report_type}-report-{datetime.datetime.now().strftime('%Y%m%d')}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def generate_csv_report(data, report_type):
    """Generate CSV report"""
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow([f"{report_type.capitalize()} Report"])
    writer.writerow(
        [f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
    )
    writer.writerow([])

    writer.writerow(["Summary"])
    for item in data["summary"]:
        writer.writerow([item["title"], item["value"]])
    writer.writerow([])

    if "items" in data and data["items"]:
        headers = [h["title"] for h in data["headers"]]
        writer.writerow(headers)

        for item in data["items"]:
            row = []
            for h in data["headers"]:
                key = h["key"]
                if key in item:
                    row.append(item[key])
                else:
                    row.append("")
            writer.writerow(row)

    buffer.seek(0)

    return send_file(
        io.BytesIO(buffer.getvalue().encode()),
        as_attachment=True,
        download_name=f"{report_type}-report-{datetime.datetime.now().strftime('%Y%m%d')}.csv",
        mimetype="text/csv",
    )