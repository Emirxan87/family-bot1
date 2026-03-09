from telegram import KeyboardButton, ReplyKeyboardMarkup


def memories_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("➕ Добавить момент"), KeyboardButton("🖼 Лента моментов")],
            [KeyboardButton("🏠 Главное меню")],
        ],
        resize_keyboard=True,
    )


def location_request_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📍 Отправить геопозицию", request_location=True)],
            [KeyboardButton("⏭ Пропустить")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
