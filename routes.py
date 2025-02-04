from flask import Blueprint, request, jsonify
from config import db

api_routes = Blueprint("api_routes", __name__)


# Get all items
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


# Add a new item
@api_routes.route("/api/items", methods=["POST"])
def add_item():
    try:
        data = request.json
        cursor = db.connection.cursor()
        cursor.execute(
            "INSERT INTO items (name, category_id, quantity, image_path) VALUES (%s, %s, %s, %s)",
            (data["name"], data["category_id"], data["quantity"], data.get("image_path")),
        )
        db.connection.commit()
        return jsonify({"message": "Item added successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Update an item
@api_routes.route("/api/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    try:
        data = request.json
        cursor = db.connection.cursor()
        cursor.execute(
            "UPDATE items SET name = %s, category_id = %s, quantity = %s, image_path = %s WHERE item_id = %s",
            (data["name"], data["category_id"], data["quantity"], data.get("image_path"), item_id),
        )
        db.connection.commit()
        return jsonify({"message": "Item updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Delete an item
@api_routes.route("/api/items/<int:item_id>", methods=["DELETE"])
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
            return jsonify({"error": "Cannot delete item, it is referenced in transactions"}), 400

        # Delete the item
        cursor.execute("DELETE FROM items WHERE item_id = %s", (item_id,))
        db.connection.commit()
        return jsonify({"message": "Item deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Get all categories
@api_routes.route("/api/categories", methods=["GET"])
def get_categories():
    try:
        cursor = db.connection.cursor()
        cursor.execute("SELECT * FROM categories")
        categories = cursor.fetchall()

        results = [
            {
                "category_id": category[0],
                "category_name": category[1],
            }
            for category in categories
        ]

        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Add categories
@api_routes.route("/api/categories", methods=["POST"])
def add_category():
    try:
        data = request.json
        if "category_name" not in data:
            return jsonify({"error": "Missing category_name"}), 400

        cursor = db.connection.cursor()
        cursor.execute("INSERT INTO categories (category_name) VALUES (%s)", (data["category_name"],))
        category_id = cursor.lastrowid
        db.connection.commit()

        return jsonify({"category_id": category_id, "category_name": data["category_name"]}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Update categories
@api_routes.route("/api/categories/<int:category_id>", methods=["PUT"])
def update_category(category_id):
    try:
        data = request.json
        if "category_name" not in data:
            return jsonify({"error": "Missing category_name"}), 400

        cursor = db.connection.cursor()
        cursor.execute("UPDATE categories SET category_name = %s WHERE category_id = %s", 
                       (data["category_name"], category_id))
        db.connection.commit()
        return jsonify({"message": "Category updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Delete categories
@api_routes.route("/api/categories/<int:category_id>", methods=["DELETE"])
def delete_category(category_id):
    try:
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM categories WHERE category_id = %s", (category_id,))
        db.connection.commit()
        return jsonify({"message": "Category deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Get all transactions
@api_routes.route("/api/transactions", methods=["GET"])
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
