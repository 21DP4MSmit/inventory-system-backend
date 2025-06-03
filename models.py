from config import db
import os


def create_tables():
    cursor = db.connection.cursor() if hasattr(db, "connection") else db.cursor()

    is_postgres = os.environ.get("DATABASE_URL") is not None

    if is_postgres:
        cursor.execute(
            """
       CREATE TABLE IF NOT EXISTS categories (
           category_id SERIAL PRIMARY KEY,
           category_name VARCHAR(50) NOT NULL
       )"""
        )

        cursor.execute(
            """
       CREATE TABLE IF NOT EXISTS items (
           item_id SERIAL PRIMARY KEY,
           name VARCHAR(100) NOT NULL,
           category_id INT NOT NULL,
           quantity INT DEFAULT 0,
           image_path VARCHAR(255) DEFAULT NULL,
           FOREIGN KEY (category_id) REFERENCES categories(category_id)
       )"""
        )

        cursor.execute(
            """
       CREATE TABLE IF NOT EXISTS users (
           user_id SERIAL PRIMARY KEY,
           username VARCHAR(50) NOT NULL UNIQUE,
           password VARCHAR(255) NOT NULL,
           role VARCHAR(20) DEFAULT 'staff'
       )"""
        )

        cursor.execute(
            """
       CREATE TABLE IF NOT EXISTS transactions (
           transaction_id SERIAL PRIMARY KEY,
           item_id INT NOT NULL,
           user_id INT NOT NULL,
           transaction_type VARCHAR(10) NOT NULL,
           quantity_change INT NOT NULL,
           transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
           notes TEXT,
           FOREIGN KEY (item_id) REFERENCES items(item_id),
           FOREIGN KEY (user_id) REFERENCES users(user_id)
       )"""
        )

        cursor.execute(
            """
       CREATE TABLE IF NOT EXISTS object_mappings (
           mapping_id SERIAL PRIMARY KEY,
           object_name VARCHAR(100) NOT NULL UNIQUE,
           category_id INT NOT NULL,
           FOREIGN KEY (category_id) REFERENCES categories(category_id)
       )"""
        )
    else:
        cursor.execute(
            """
       CREATE TABLE IF NOT EXISTS categories (
           category_id INT AUTO_INCREMENT PRIMARY KEY,
           category_name VARCHAR(50) NOT NULL
       )"""
        )

        cursor.execute(
            """
       CREATE TABLE IF NOT EXISTS items (
           item_id INT AUTO_INCREMENT PRIMARY KEY,
           name VARCHAR(100) NOT NULL,
           category_id INT NOT NULL,
           quantity INT DEFAULT 0,
           image_path VARCHAR(255) DEFAULT NULL,
           FOREIGN KEY (category_id) REFERENCES categories(category_id)
       )"""
        )

        cursor.execute(
            """
       CREATE TABLE IF NOT EXISTS users (
           user_id INT AUTO_INCREMENT PRIMARY KEY,
           username VARCHAR(50) NOT NULL UNIQUE,
           password VARCHAR(255) NOT NULL,
           role ENUM('admin', 'staff') DEFAULT 'staff'
       )"""
        )

        cursor.execute(
            """
       CREATE TABLE IF NOT EXISTS transactions (
           transaction_id INT AUTO_INCREMENT PRIMARY KEY,
           item_id INT NOT NULL,
           user_id INT NOT NULL,
           transaction_type ENUM('in', 'out') NOT NULL,
           quantity_change INT NOT NULL,
           transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
           notes TEXT,
           FOREIGN KEY (item_id) REFERENCES items(item_id),
           FOREIGN KEY (user_id) REFERENCES users(user_id)
       )"""
        )

        cursor.execute(
            """
       CREATE TABLE IF NOT EXISTS object_mappings (
           mapping_id INT AUTO_INCREMENT PRIMARY KEY,
           object_name VARCHAR(100) NOT NULL UNIQUE,
           category_id INT NOT NULL,
           FOREIGN KEY (category_id) REFERENCES categories(category_id)
       )"""
        )

    if hasattr(db, "connection"):
        db.connection.commit()


def get_object_mappings():
    cursor = db.connection.cursor() if hasattr(db, "connection") else db.cursor()
    cursor.execute(
        """
       SELECT om.object_name, c.category_name, om.category_id 
       FROM object_mappings om
       JOIN categories c ON om.category_id = c.category_id
   """
    )

    mappings = {}
    for row in cursor.fetchall():
        mappings[row[0]] = {"category_name": row[1], "category_id": row[2]}

    return mappings


def add_object_mapping(object_name, category_id):
    try:
        cursor = db.connection.cursor() if hasattr(db, "connection") else db.cursor()

        cursor.execute(
            "SELECT mapping_id FROM object_mappings WHERE object_name = %s",
            (object_name,),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                "UPDATE object_mappings SET category_id = %s WHERE object_name = %s",
                (category_id, object_name),
            )
        else:
            cursor.execute(
                "INSERT INTO object_mappings (object_name, category_id) VALUES (%s, %s)",
                (object_name, category_id),
            )

        if hasattr(db, "connection"):
            db.connection.commit()
        return True
    except Exception as e:
        print(f"Error adding object mapping: {str(e)}")
        return False
