import logging
import os
import asyncio
import sqlite3
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from database import get_products
from database import is_admin
from database import save_user
from database import save_barber
from database import update_barber
from database import remove_barber
from database import get_all_barbers
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.filters import CommandObject  # Импортируем для работы с аргументами команды
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
import datetime

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")  # Укажи ID администратора

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Подключение Google Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro")

# Обработчик команды /start
@dp.message(Command("start"))
async def start_command(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 Отправить номер", request_contact=True)]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
    await message.answer("👋 Добро пожаловать в барбершоп!\nОтправьте ваш номер телефона нажав на кнопку:", reply_markup=keyboard)



# Обработчик получения номера телефона
@dp.message(F.contact)
async def save_phone(message: types.Message):
    if not message.contact:
        await message.answer("❌ Ошибка! Отправьте номер, нажав кнопку ниже.")
        return

    user_id = message.from_user.id
    full_name = message.from_user.full_name
    phone_number = message.contact.phone_number

    save_user(user_id, full_name, phone_number)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Записаться на стрижку", callback_data="book")],
        [InlineKeyboardButton(text="🛒 Купить укладочные средства", callback_data="shop")],
        [InlineKeyboardButton(text="💬 Спросить у ИИ - ассистента", callback_data="gemini_chat")]
    ])
    await message.answer("✅ Ваш номер сохранен! Выберите действие:", reply_markup=keyboard)




@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💈 Барберы", callback_data="manage_barbers")],
        [InlineKeyboardButton(text="📋 Управление записями", callback_data="manage_bookings")],
        [InlineKeyboardButton(text="📦 Товары", callback_data="manage_products")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]

    ])
    await message.answer("🔧 Админ-панель:", reply_markup=keyboard)

# Функция для создания клавиатуры админ-панели
def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💈 Барберы", callback_data="manage_barbers")],
        [InlineKeyboardButton(text="📋 Управление записями", callback_data="manage_bookings")],
        [InlineKeyboardButton(text="📦 Товары", callback_data="manage_products")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]
    ])

# Обработчик кнопки управления барберами
@dp.callback_query(F.data == "manage_barbers")
async def manage_barbers_menu(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить барбера", callback_data="add_barber")],
        [InlineKeyboardButton(text="📋 Список барберов", callback_data="list_barbers")],
        [InlineKeyboardButton(text="✏ Изменить барбера", callback_data="edit_barber")],
        [InlineKeyboardButton(text="❌ Удалить барбера", callback_data="delete_barber")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]
    ])
    await callback.message.answer("💈 Управление барберами:", reply_markup=keyboard)

class AddBarber(StatesGroup):
    name = State()
    specialization = State()
    photo = State()

@dp.callback_query(F.data == "add_barber")
async def add_barber_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddBarber.name)
    await callback.message.answer("Введите имя барбера:")

@dp.message(AddBarber.name)
async def add_barber_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddBarber.specialization)
    await message.answer("Введите специализацию барбера:")

@dp.message(AddBarber.specialization)
async def add_barber_specialization(message: types.Message, state: FSMContext):
    await state.update_data(specialization=message.text)
    await state.set_state(AddBarber.photo)
    await message.answer("Отправьте фото барбера:")

@dp.message(AddBarber.photo, F.photo)
async def add_barber_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id  # Получаем ID фото
    data = await state.get_data()

    save_barber(data["name"], data["specialization"], photo_id)
    await state.clear()
    await message.answer("✅ Барбер добавлен!")


class EditBarber(StatesGroup):
    barber_id = State()
    new_name = State()
    new_specialization = State()
    new_photo = State()

@dp.callback_query(F.data == "edit_barber")
async def edit_barber_start(callback: types.CallbackQuery, state: FSMContext):
    barbers = get_all_barbers()
    if not barbers:
        await callback.message.answer("❌ Нет барберов для редактирования.")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{barber[1]}", callback_data=f"edit_{barber[0]}")]
        for barber in barbers
    ])
    await callback.message.answer("Выберите барбера для редактирования:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("edit_"))
async def select_barber_to_edit(callback: types.CallbackQuery, state: FSMContext):
    barber_id = int(callback.data.split("_")[1])
    await state.update_data(barber_id=barber_id)
    await state.set_state(EditBarber.new_name)
    await callback.message.answer("Введите новое имя барбера:")

@dp.message(EditBarber.new_name)
async def edit_barber_name(message: types.Message, state: FSMContext):
    await state.update_data(new_name=message.text)
    await state.set_state(EditBarber.new_specialization)
    await message.answer("Введите новую специализацию:")

@dp.message(EditBarber.new_specialization)
async def edit_barber_specialization(message: types.Message, state: FSMContext):
    await state.update_data(new_specialization=message.text)
    await state.set_state(EditBarber.new_photo)
    await message.answer("Отправьте новое фото (или напишите 'нет', чтобы оставить старое):")

@dp.message(EditBarber.new_photo, F.photo | F.text)
async def edit_barber_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id if message.photo else None

    update_barber(data["barber_id"], data["new_name"], data["new_specialization"], photo_id)
    await state.clear()
    await message.answer("✅ Информация о барбере обновлена!")

#спиок барберов
@dp.callback_query(F.data == "list_barbers")
async def list_barbers(callback: types.CallbackQuery):
    barbers = get_all_barbers()

    if not barbers:
        await callback.message.answer("❌ В списке нет барберов.")
        return

    text = "💈 <b>Список барберов:</b>\n\n"
    for barber in barbers:
        text += f"🔹 <b>{barber[1]}</b> (ID: {barber[0]})\n"

    await callback.message.answer(text, parse_mode="HTML")


# удаление барбера
@dp.callback_query(F.data == "delete_barber")
async def delete_barber_start(callback: types.CallbackQuery):
    barbers = get_all_barbers()
    if not barbers:
        await callback.message.answer("❌ Нет барберов для удаления.")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"❌ {barber[1]}", callback_data=f"delete_{barber[0]}")]
        for barber in barbers
    ])
    await callback.message.answer("Выберите барбера для удаления:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("delete_"))
async def delete_barber(callback: types.CallbackQuery):
    barber_id = int(callback.data.split("_")[1])
    remove_barber(barber_id)
    await callback.message.answer("✅ Барбер удален!")


# Обработчик кнопки управления записями
@dp.callback_query(lambda c: c.data == "manage_bookings")
async def manage_bookings(callback_query: CallbackQuery):
    bookings = get_bookings()
    if not bookings:
        await callback_query.message.answer("❌ Нет записей на стрижку.")
        await callback_query.answer()
        return

    for book in bookings:
        book_id, user_name, barber_name, date, time = book
        text = f"👤 Клиент: {user_name}\n💈 Барбер: {barber_name}\n📅 Дата: {date}\n⏰ Время: {time}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏ Изменить", callback_data=f"edit_{book_id}")],
            [InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_{book_id}")],
            [InlineKeyboardButton(text="✅ Оставить", callback_data="ignore")]
        ])
        await callback_query.message.answer(text, reply_markup=keyboard)
    await callback_query.answer()

@dp.callback_query(F.data == "admin_menu")
async def admin_menu(callback: types.CallbackQuery):
    await callback.message.answer("🔧 Админ-панель:", reply_markup=admin_keyboard())


# Функции для работы с записями

def get_bookings():
    conn = sqlite3.connect("barbershop.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT bookings.id, users.full_name, barbers.name, bookings.date, bookings.time
        FROM bookings
        JOIN users ON bookings.user_id = users.id
        JOIN barbers ON bookings.barber_id = barbers.id
        ORDER BY bookings.date, bookings.time
    """)
    bookings = cursor.fetchall()
    conn.close()
    print("DEBUG: get_bookings() ->", bookings)  # Вывод отладочной информации
    return bookings

def update_booking(booking_id, new_date=None, new_time=None, new_barber_id=None):
    conn = sqlite3.connect("barbershop.db")
    cursor = conn.cursor()
    if new_date:
        cursor.execute("UPDATE bookings SET date = ? WHERE id = ?", (new_date, booking_id))
    if new_time:
        cursor.execute("UPDATE bookings SET time = ? WHERE id = ?", (new_time, booking_id))
    if new_barber_id:
        cursor.execute("UPDATE bookings SET barber_id = ? WHERE id = ?", (new_barber_id, booking_id))
    conn.commit()
    conn.close()

def delete_booking(booking_id):
    conn = sqlite3.connect("barbershop.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()


# Обработчик удаления записи
@dp.callback_query(lambda c: c.data.startswith("delete_"))
async def delete_booking_handler(callback_query: CallbackQuery):
    booking_id = int(callback_query.data.split("_")[1])
    delete_booking(booking_id)
    await callback_query.message.answer("✅ Запись удалена.")
    await callback_query.answer()

# Обработчик изменения записи
@dp.callback_query(lambda c: c.data.startswith("edit_"))
async def edit_booking_handler(callback_query: CallbackQuery):
    booking_id = callback_query.data.split("_")[1]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Дата", callback_data=f"edit_date_{booking_id}")],
        [InlineKeyboardButton(text="⏰ Время", callback_data=f"edit_time_{booking_id}")],
        [InlineKeyboardButton(text="💇 Барбер", callback_data=f"edit_barber_{booking_id}")]
    ])
    await callback_query.message.answer("🔧 Что изменить?", reply_markup=keyboard)
    await callback_query.answer()



# Подключение к базе данных (для записи на стрижку)
def get_barbers():
    conn = sqlite3.connect("barbershop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM barbers")
    barbers = cursor.fetchall()
    conn.close()
    return barbers

def get_booked_slots(barber_id, date):
    conn = sqlite3.connect("barbershop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT time FROM bookings WHERE barber_id = ? AND date = ?", (barber_id, date))
    booked_times = {row[0] for row in cursor.fetchall()}
    conn.close()
    return booked_times

def save_booking(user_id, barber_id, date, time):
    conn = sqlite3.connect("barbershop.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO bookings (user_id, barber_id, date, time) VALUES (?, ?, ?, ?)",
                   (user_id, barber_id, date, time))
    conn.commit()
    conn.close()

def get_barber_name(barber_id):
    conn = sqlite3.connect("barbershop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM barbers WHERE id = ?", (barber_id,))
    barber_name = cursor.fetchone()
    conn.close()
    return barber_name[0] if barber_name else "Неизвестный барбер"

# Обработчик кнопки "Купить укладочные средства"
@dp.callback_query(lambda c: c.data == "shop")
async def shop_catalog(callback_query: CallbackQuery):
    products = get_products()
    if not products:
        await callback_query.message.answer("❌ В данный момент нет товаров для покупки.")
        await callback_query.answer()
        return

    for prod in products:
        prod_id, name, price, desc, photo_url = prod
        text = f"{name}\nЦена: {price}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Подробнее", callback_data=f"prodinfo_{prod_id}"),
                InlineKeyboardButton(text="Купить", callback_data=f"buy_{prod_id}")
            ]
        ])

        if photo_url:
            try:
                with open(photo_url, 'rb') as photo:
                    await callback_query.message.answer_photo(
                        photo=photo,
                        caption=text,
                        reply_markup=keyboard
                    )
            except Exception as e:
                logging.error(f"Ошибка загрузки фото: {e}")
                await callback_query.message.answer(text, reply_markup=keyboard)
        else:
            await callback_query.message.answer(text, reply_markup=keyboard)
    
    await callback_query.answer()

# Функция для сохранения нового пользователя в базе данных
def save_user(user_id, full_name, phone):
    conn = sqlite3.connect("barbershop.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id, full_name, phone) VALUES (?, ?, ?)", (user_id, full_name, phone))
    conn.commit()
    conn.close()

# Главное меню
#@dp.message(Command("start"))
#async def start_command(message: types.Message):
    #keyboard = InlineKeyboardMarkup(inline_keyboard=[
        #[InlineKeyboardButton(text="📅 Записаться на стрижку", callback_data="book")],
        #[InlineKeyboardButton(text="🛒 Купить укладочные средства", callback_data="shop")],
        #[InlineKeyboardButton(text="💬 Спросить у ИИ - ассистента", callback_data="gemini_chat")]
    #])
    #await message.answer("👋 Добро пожаловать в барбершоп!\nВыберите действие:", reply_markup=keyboard)



# Обработчик общения с Gemini
@dp.callback_query(lambda c: c.data == "gemini_chat")
async def gemini_chat_start(callback_query: CallbackQuery):
    await callback_query.message.answer("💬 Отправьте мне вопрос, и я отвечу с помощью Google Gemini.")
    await callback_query.answer()

@dp.message()
async def gemini_chat(message: types.Message):
    response = model.generate_content(message.text)
    await message.answer(response.text)

# Обработчик кнопки "Записаться на стрижку"
@dp.callback_query(lambda c: c.data == "book")
async def book_appointment(callback_query: CallbackQuery):
    barbers = get_barbers()
    if not barbers:
        await callback_query.message.answer("❌ В данный момент нет доступных барберов.")
        await callback_query.answer()
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=barber[1], callback_data=f"barber_{barber[0]}")]
        for barber in barbers
    ])
    await callback_query.message.answer("Выберите барбера:", reply_markup=keyboard)
    await callback_query.answer()

# Обработчик выбора барбера
@dp.callback_query(lambda c: c.data.startswith("barber_"))
async def select_barber(callback_query: CallbackQuery):
    barber_id = callback_query.data.split("_")[1]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for i in range(7):
        date = (datetime.datetime.now() + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=date, callback_data=f"date_{barber_id}_{date}")]
        )
    await callback_query.message.answer("Выберите дату:", reply_markup=keyboard)
    await callback_query.answer()

# Обработчик выбора даты
@dp.callback_query(lambda c: c.data.startswith("date_"))
async def select_date(callback_query: CallbackQuery):
    _, barber_id, date = callback_query.data.split("_")
    booked_slots = get_booked_slots(barber_id, date)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for hour in range(9, 22):
        time_slot = f"{hour}:00"
        if time_slot not in booked_slots:
            keyboard.inline_keyboard.append(
                [InlineKeyboardButton(text=time_slot, callback_data=f"time_{barber_id}_{date}_{time_slot}")]
            )
    if keyboard.inline_keyboard:
        await callback_query.message.answer("Выберите время:", reply_markup=keyboard)
    else:
        await callback_query.message.answer("❌ На эту дату уже нет свободных мест.")
    await callback_query.answer()

# Обработчик выбора времени
@dp.callback_query(lambda c: c.data.startswith("time_"))
async def select_time(callback_query: CallbackQuery):
    _, barber_id, date, time = callback_query.data.split("_")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить запись", callback_data=f"confirm_{barber_id}_{date}_{time}")]
    ])
    await callback_query.message.answer(f"Вы выбрали {time} на {date}. Подтвердите запись:", reply_markup=keyboard)
    await callback_query.answer()

# Обработчик подтверждения записи
@dp.callback_query(lambda c: c.data.startswith("confirm_"))
async def confirm_booking(callback_query: CallbackQuery):
    _, barber_id, date, time = callback_query.data.split("_")
    user_id = callback_query.from_user.id
    barber_name = get_barber_name(barber_id)
    save_booking(user_id, barber_id, date, time)
    await callback_query.message.answer(
        f"✅ Запись подтверждена!\n💈 Барбер: {barber_name}\n📅 Дата: {date}\n🕒 Время: {time}"
    )
    if ADMIN_ID:
        await bot.send_message(
            ADMIN_ID,
            f"Новая запись:\n👤 Клиент: {callback_query.from_user.full_name}\n💈 Барбер: {barber_name}\n📅 Дата: {date}\n🕒 Время: {time}"
        )
    await callback_query.answer()




# Обработчик запроса "Подробнее" о товаре
@dp.callback_query(lambda c: c.data.startswith("prodinfo_"))
async def product_info(callback_query: CallbackQuery):
    product_id = int(callback_query.data.split("_")[1])

    # Получаем данные о товаре
    conn = sqlite3.connect("barbershop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, description, photo_url FROM products WHERE id=?", (product_id,))
    product = cursor.fetchone()
    conn.close()

    if not product:
        await callback_query.message.answer("❌ Товар не найден.")
        await callback_query.answer()
        return

    name, price, desc, photo_url = product

    # Проверяем, есть ли фото
    text = f"{name}\nЦена: {price}\nОписание: {desc}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить", callback_data=f"buy_{product_id}")]
    ])

    try:
        if photo_url.startswith("http"):
            await callback_query.message.answer_photo(photo=photo_url, caption=text, reply_markup=keyboard)
        else:
            photo = FSInputFile(photo_url)  # Используем FSInputFile для локального файла
            await callback_query.message.answer_photo(photo=photo, caption=text, reply_markup=keyboard)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка при загрузке фото: {e}")



    await callback_query.answer()


# Обработчик покупки товара
@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_product(callback_query: CallbackQuery):
    _, prod_id = callback_query.data.split("_")
    products = get_products()
    product = next((p for p in products if p[0] == int(prod_id)), None)
    if not product:
        await callback_query.message.answer("❌ Товар не найден.")
        await callback_query.answer()
        return
    await callback_query.message.answer(
        f"✅ Заказ на товар '{product[1]}' принят! Мы свяжемся с вами для подтверждения заказа."
    )
    await callback_query.answer()




# Запуск бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
