from telegram import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🛒 Покупки"), KeyboardButton("📅 Календарь")],
            [KeyboardButton("💰 Расходы"), KeyboardButton("📸 Моменты")],
            [KeyboardButton("👨‍👩‍👧‍👦 Семья"), KeyboardButton("⚙️ Ещё")],
        ],
        resize_keyboard=True,
    )
