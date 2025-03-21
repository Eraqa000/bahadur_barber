import sqlite3

def add_user(user_id, full_name, phone):
    conn = sqlite3.connect("barbershop.db")
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO users (user_id, full_name, phone) VALUES (?, ?, ?)", 
                   (user_id, full_name, phone))
    
    conn.commit()
    conn.close()

# Примеры барберов
users = [
    ("1094852763", "Aiqyn", "87471624562"),
]

for user in users:
    add_user(*user)
