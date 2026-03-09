from telegram import KeyboardButton, ReplyKeyboardMarkup


def calendar_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("➕ Добавить событие"), KeyboardButton("📆 Сегодня")],
            [KeyboardButton("🏠 Главное меню")],
        ],
        resize_keyboard=True,
    )
