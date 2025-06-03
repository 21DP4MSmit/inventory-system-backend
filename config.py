from flask_mysqldb import MySQL
from flask import Flask
import os
import psycopg2
from urllib.parse import urlparse

app = Flask(__name__)

if os.environ.get('DATABASE_URL'):
    database_url = os.environ.get('DATABASE_URL')
    url = urlparse(database_url)

    app.config['POSTGRES_HOST'] = url.hostname
    app.config['POSTGRES_PORT'] = url.port
    app.config['POSTGRES_DB'] = url.path[1:]
    app.config['POSTGRES_USER'] = url.username
    app.config['POSTGRES_PASSWORD'] = url.password
    app.config['DATABASE_URL'] = database_url
    app.config['DB_TYPE'] = 'postgresql'

    class PostgreSQLConnection:
        def __init__(self):
            self.connection = None
            self.connect()
        
        def connect(self):
            try:
                self.connection = psycopg2.connect(
                    host=app.config['POSTGRES_HOST'],
                    port=app.config['POSTGRES_PORT'],
                    database=app.config['POSTGRES_DB'],
                    user=app.config['POSTGRES_USER'],
                    password=app.config['POSTGRES_PASSWORD']
                )
                self.connection.autocommit = True
            except Exception as e:
                print(f"PostgreSQL connection error: {e}")
                self.connection = None
        
        def cursor(self):
            if not self.connection:
                self.connect()
            return self.connection.cursor()
    
    db = PostgreSQLConnection()

else:
    app.config["MYSQL_HOST"] = "localhost"
    app.config["MYSQL_USER"] = "root"
    app.config["MYSQL_PASSWORD"] = ""
    app.config["MYSQL_DB"] = "inventory_db"
    app.config['DB_TYPE'] = 'mysql'
    
    db = MySQL(app)