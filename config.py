from flask_mysqldb import MySQL
from flask import Flask
import os

app = Flask(__name__)

if os.environ.get("CLOUD_SQL_CONNECTION_NAME"):
    app.config["MYSQL_HOST"] = "localhost"
    app.config["MYSQL_USER"] = "root"
    app.config["MYSQL_PASSWORD"] = os.environ.get("DB_PASSWORD")
    app.config["MYSQL_DB"] = os.environ.get("DB_NAME", "inventory_db")
    app.config["MYSQL_UNIX_SOCKET"] = f"/cloudsql/{os.environ.get('CLOUD_SQL_CONNECTION_NAME')}"
    app.config["MYSQL_CHARSET"] = "utf8mb4"
    app.config["DB_TYPE"] = "mysql"
    
    db = MySQL(app)
    print("Connected to Cloud SQL MySQL via Unix socket")
    
elif os.environ.get("DATABASE_URL"):
    from urllib.parse import urlparse
    url = urlparse(os.environ.get("DATABASE_URL"))
    
    app.config["MYSQL_HOST"] = url.hostname
    app.config["MYSQL_PORT"] = url.port or 3306
    app.config["MYSQL_USER"] = url.username
    app.config["MYSQL_PASSWORD"] = url.password
    app.config["MYSQL_DB"] = url.path[1:]
    app.config["MYSQL_CHARSET"] = "utf8mb4"
    app.config["DB_TYPE"] = "mysql"
    
    db = MySQL(app)
    print("Connected to MySQL via connection string")
    
else:
    app.config["MYSQL_HOST"] = "localhost"
    app.config["MYSQL_USER"] = "root"
    app.config["MYSQL_PASSWORD"] = ""
    app.config["MYSQL_DB"] = "inventory_db"
    app.config["MYSQL_CHARSET"] = "utf8mb4"
    app.config["DB_TYPE"] = "mysql"
    
    db = MySQL(app)
    print("Connected to local MySQL")