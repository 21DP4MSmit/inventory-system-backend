import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import app, db
from routes import api_routes
from auth import auth_routes
from models import create_tables

CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    supports_credentials=True,
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Confidence-Threshold"],
)

app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config["JWT_COOKIE_SECURE"] = False
app.config["JWT_COOKIE_CSRF_PROTECT"] = False

app.config["JWT_SECRET_KEY"] = (
    "24dbdf01c1042bf4d7e55a223ef8fd479a6964308c1fd491d092172fe062c8b2"
)

if os.environ.get("DATABASE_URL"):
    app.config["MYSQL_HOST"] = os.environ.get("MYSQL_HOST")
    app.config["MYSQL_USER"] = os.environ.get("MYSQL_USER")
    app.config["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD")
    app.config["MYSQL_DB"] = os.environ.get("MYSQL_DB")

jwt = JWTManager(app)

app.register_blueprint(api_routes)
app.register_blueprint(auth_routes)

with app.app_context():
    try:
        print("Attempting to initialize database schema...")
        create_tables()
        print("Database schema check/creation complete.")
    except Exception as e:
        print(f"ERROR during database schema initialization: {e}")


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
