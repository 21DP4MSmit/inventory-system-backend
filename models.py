from config import db


def create_tables():
    cursor = db.connection.cursor()

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

    db.connection.commit()
