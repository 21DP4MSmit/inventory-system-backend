from config import db

def create_tables():
    cursor = db.connection.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        category VARCHAR(100),
        stock INT DEFAULT 0,
        image_url TEXT
    )""")
    db.connection.commit()
