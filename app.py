from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import app, db
from routes import api_routes
from auth import auth_routes

CORS(app, supports_credentials=True)
app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config["JWT_COOKIE_SECURE"] = False  # Change to True in production
app.config["JWT_COOKIE_CSRF_PROTECT"] = False


app.config["JWT_SECRET_KEY"] = "24dbdf01c1042bf4d7e55a223ef8fd479a6964308c1fd491d092172fe062c8b2"

jwt = JWTManager(app)

app.register_blueprint(api_routes)
app.register_blueprint(auth_routes)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
