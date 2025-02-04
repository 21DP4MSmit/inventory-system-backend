from flask import Blueprint, request, jsonify
from config import db

api_routes = Blueprint("api_routes", __name__)

# Get all items
@api_routes.route("/api/items", methods=["GET"])
def get_items():
    cursor = db.connection.cursor()
    cursor.execute("SELECT * FROM items")
    items = cursor.fetchall()
    
    results = []
    for item in items:
        results.append({
            "item_id": item[0],
            "name": item[1],
            "category_id": item[2],
            "quantity": item[3],
            "image_path": item[4]
        })

    return jsonify(results)

# Add new item
@api_routes.route("/api/items", methods=["POST"])
def add_item():
    data = request.json
    cursor = db.connection.cursor()
    cursor.execute(
        "INSERT INTO items (name, category_id, quantity, image_path) VALUES (%s, %s, %s, %s)",
        (data["name"], data["category_id"], data["quantity"], data.get("image_path")),
    )
    db.connection.commit()
    return jsonify({"message": "Item added successfully"}), 201


# Delete an item
@api_routes.route("/api/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    cursor = db.connection.cursor()
    cursor.execute("DELETE FROM items WHERE item_id = %s", (item_id,))
    db.connection.commit()
    return jsonify({"message": "Item deleted successfully"})


# Get all categories
@api_routes.route("/api/categories", methods=["GET"])
def get_categories():
    cursor = db.connection.cursor()
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    
    results = []
    for category in categories:
        results.append({
            "category_id": category[0],
            "category_name": category[1]
        })

    return jsonify(results)


# Get all transactions
@api_routes.route("/api/transactions", methods=["GET"])
def get_transactions():
    cursor = db.connection.cursor()
    cursor.execute("SELECT * FROM transactions")
    transactions = cursor.fetchall()
    
    results = []
    for transaction in transactions:
        results.append({
            "transaction_id": transaction[0],
            "item_id": transaction[1],
            "user_id": transaction[2],
            "transaction_type": transaction[3],
            "quantity_change": transaction[4],
            "transaction_date": str(transaction[5])
        })

    return jsonify(results)
