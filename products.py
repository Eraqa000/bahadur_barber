import sqlite3

DB_NAME = "barbershop.db"

def delete_all_users():
    """Удаляет все записи из таблицы users."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users;")  # Удаляем все записи
    conn.commit()
    
    print("Все записи удалены из таблицы users.")

    conn.close()

if __name__ == "__main__":
    delete_all_users()
