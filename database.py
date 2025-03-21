import sqlite3

DB_NAME = "barbershop.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Таблица админов
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            full_name TEXT,
            phone TEXT
        );
    """)

    conn.commit()
    conn.close()

# Изменение имени барбера
def update_barber_name(barber_id, new_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE barbers SET name = ? WHERE id = ?", (new_name, barber_id))
    conn.commit()
    conn.close()

# Изменение специализации
def update_barber_specialization(barber_id, new_specialization):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE barbers SET specialization = ? WHERE id = ?", (new_specialization, barber_id))
    conn.commit()
    conn.close()

# Изменение фото
def update_barber_photo(barber_id, new_photo):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE barbers SET photo = ? WHERE id = ?", (new_photo, barber_id))
    conn.commit()
    conn.close()

def save_barber(name, specialization, photo):
    conn = sqlite3.connect("barbershop.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO barbers (name, specialization, photo) VALUES (?, ?, ?)", 
                   (name, specialization, photo))
    conn.commit()
    conn.close()

def update_barber(barber_id, name, specialization, photo):
    conn = sqlite3.connect("barbershop.db")
    cursor = conn.cursor()
    if photo:
        cursor.execute("UPDATE barbers SET name=?, specialization=?, photo=? WHERE id=?", 
                       (name, specialization, photo, barber_id))
    else:
        cursor.execute("UPDATE barbers SET name=?, specialization=? WHERE id=?", 
                       (name, specialization, barber_id))
    conn.commit()
    conn.close()

def remove_barber(barber_id):
    conn = sqlite3.connect("barbershop.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM barbers WHERE id=?", (barber_id,))
    conn.commit()
    conn.close()

def get_all_barbers():
    conn = sqlite3.connect("barbershop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM barbers")
    barbers = cursor.fetchall()
    conn.close()
    return barbers





#def update_photo_path(product_id, new_path):
    #"""Обновляет путь к фото для товара с указанным ID."""
    #conn = sqlite3.connect(DB_NAME)
    #cursor = conn.cursor()
   # cursor.execute("UPDATE products SET photo_url = ? WHERE id = ?", (new_path, product_id))
   # conn.commit()
    #conn.close()

def get_products():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, description, photo_url FROM products")
    products = cursor.fetchall()
    conn.close()
    return products

def is_admin(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM admins WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    return result is not None

def save_user(user_id, full_name, phone):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, full_name, phone) 
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET 
        full_name = excluded.full_name, 
        phone = excluded.phone
    """, (user_id, full_name, phone))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("База данных успешно инициализирована!")

    # Обновляем путь фото для товара с ID 1
    #update_photo_path(3, r"C:\Users\lenovo\Desktop\burbershop_bot\image\product_3.jpg")
    print("Путь к фото обновлён!")
