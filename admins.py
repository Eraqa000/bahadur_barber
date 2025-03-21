import sqlite3

def add_admin(user_id):
    conn = sqlite3.connect("barbershop.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute("INSERT INTO admins (user_id) VALUES (?)", (user_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        print("Этот админ уже есть в базе.")
    
    conn.close()

# Добавляем себя как админа
add_admin(999900036)
