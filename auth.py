from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash
from config import db

# Create a blueprint for authentication routes
auth_routes = Blueprint("auth_routes", __name__)


@auth_routes.route("/api/login", methods=["POST"])
def login():
    try:
        data = request.json
        username = data.get("username")
        password = data.get("password")

        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT user_id, username, password, role FROM users WHERE username = %s",
            (username,),
        )
        user = cursor.fetchone()

        if user and check_password_hash(user[2], password):
            user_data = {"id": str(user[0]), "username": user[1], "role": user[3]}

            access_token = create_access_token(
                identity=user_data["id"],
                additional_claims={
                    "username": user_data["username"],
                    "role": user_data["role"],
                },
            )

            return jsonify({"access_token": access_token, "user": user_data}), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_routes.route("/api/protected", methods=["GET"])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200
