from flask_mysqldb import MySQL
from flask import Flask

app = Flask(__name__)

# Database Config
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "inventory_db"

db = MySQL(app)
