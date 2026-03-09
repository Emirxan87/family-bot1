from telegram import KeyboardButton, ReplyKeyboardMarkup


def expenses_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("➕ Добавить расход"), KeyboardButton("📃 Последние расходы")],
            [KeyboardButton("📊 Сводка"), KeyboardButton("🏠 Главное меню")],
        ],
        resize_keyboard=True,
    )
