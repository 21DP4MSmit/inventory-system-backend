from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from config import db
from werkzeug.security import check_password_hash, generate_password_hash
import re

api_routes = Blueprint("api_routes", __name__)


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


# Get all items (public route)
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


# Add a new item (admin and staff)
@api_routes.route("/api/items", methods=["POST"])
@role_required(["admin", "staff"])
def add_item():
    try:
        data = request.json
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
        db.connection.commit()
        return jsonify({"message": "Item added successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Update an item (admin and staff)
@api_routes.route("/api/items/<int:item_id>", methods=["PUT"])
@role_required(["admin", "staff"])
def update_item(item_id):
    try:
        data = request.json
        cursor = db.connection.cursor()
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


# Get all categories (staff and admin)
@api_routes.route("/api/categories", methods=["GET"])
@jwt_required()
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
        cursor.execute("DELETE FROM categories WHERE category_id = %s", (category_id,))
        db.connection.commit()
        return jsonify({"message": "Category deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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

        # Validate fields
        if not data.get("username"):
            return jsonify({"errors": {"username": ["Username is required."]}}), 422
        if not data.get("password"):
            return jsonify({"errors": {"password": ["Password is required."]}}), 422
        if not data.get("role"):
            return jsonify({"errors": {"role": ["Role is required."]}}), 422

        # Validate password
        validation_error = validate_password(data["password"])
        if validation_error:
            return jsonify({"errors": {"password": [validation_error]}}), 422

        # Insert into the database
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


# Update a user (admin and staff)
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
            # Validate the new password
            validation_error = validate_password(data["password"])
            if validation_error:
                return jsonify({"errors": {"password": validation_error}}), 422

            updates.append("password = %s")
            params.append(generate_password_hash(data["password"]))

        # Handle role update
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


# Get all transactions (admin)
@api_routes.route("/api/transactions", methods=["GET"])
@role_required(["admin"])
def get_transactions():
    try:
        cursor = db.connection.cursor()
        cursor.execute("SELECT * FROM transactions")
        transactions = cursor.fetchall()

        results = [
            {
                "transaction_id": transaction[0],
                "item_id": transaction[1],
                "user_id": transaction[2],
                "transaction_type": transaction[3],
                "quantity_change": transaction[4],
                "transaction_date": str(transaction[5]),
            }
            for transaction in transactions
        ]

        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
