from flask import Flask
from flask_cors import CORS
from config import app, db
from routes import api_routes

CORS(app)

# Register API Routes
app.register_blueprint(api_routes)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
