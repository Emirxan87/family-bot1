from telegram import KeyboardButton, ReplyKeyboardMarkup


def family_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("➕ Создать семью"), KeyboardButton("🔑 Вступить по коду")],
            [KeyboardButton("👥 Участники"), KeyboardButton("🏠 Главное меню")],
        ],
        resize_keyboard=True,
    )
