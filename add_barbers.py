import sqlite3

def add_barber(name, specialization, photo):
    conn = sqlite3.connect("barbershop.db")
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO barbers (name, specialization, photo) VALUES (?, ?, ?)", 
                   (name, specialization, photo))
    
    conn.commit()
    conn.close()

# Примеры барберов
barbers = [
    ("Иван", "Fade, классика", "ivan.jpg"),
    ("Алексей", "Бородист, стиль", "alexey.jpg"),
    ("Михаил", "Креативные стрижки", "mikhail.jpg")
]

for barber in barbers:
    add_barber(*barber)

print("Барберы добавлены в базу!")
