from flask import Flask
from flask_cors import CORS
from routes import api_routes
from config import db

app = Flask(__name__)
CORS(app)

# Register Routes
app.register_blueprint(api_routes)

if __name__ == "__main__":
    app.run(debug=True)
