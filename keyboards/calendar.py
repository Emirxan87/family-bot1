from telegram import KeyboardButton, ReplyKeyboardMarkup


def calendar_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("➕ Добавить событие")],
            [KeyboardButton("📅 Сегодня"), KeyboardButton("🌤 Завтра")],
            [KeyboardButton("📋 Ближайшие 7 дней"), KeyboardButton("🗓 По дате")],
            [KeyboardButton("👨‍👩‍👧 Все семейные события")],
            [KeyboardButton("🏠 Главное меню")],
        ],
        resize_keyboard=True,
    )


def event_type_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🏥 Врач"), KeyboardButton("🎂 День рождения")],
            [KeyboardButton("🏫 Школа / садик"), KeyboardButton("💼 Работа")],
            [KeyboardButton("🛒 Покупки / дела"), KeyboardButton("🚗 Поездка")],
            [KeyboardButton("🧾 Платёж"), KeyboardButton("📌 Другое")],
            [KeyboardButton("❌ Отмена")],
        ],
        resize_keyboard=True,
    )


def event_date_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📅 Сегодня"), KeyboardButton("🌤 Завтра")],
            [KeyboardButton("🗓 Выбрать дату")],
            [KeyboardButton("❌ Отмена")],
        ],
        resize_keyboard=True,
    )


def event_time_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("Без времени")],
            [KeyboardButton("🌅 Утро"), KeyboardButton("☀️ День"), KeyboardButton("🌆 Вечер")],
            [KeyboardButton("⏰ Ввести время")],
            [KeyboardButton("❌ Отмена")],
        ],
        resize_keyboard=True,
    )


def event_participant_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("На меня"), KeyboardButton("На другого члена семьи")],
            [KeyboardButton("👨‍👩‍👧 Общее")],
            [KeyboardButton("❌ Отмена")],
        ],
        resize_keyboard=True,
    )


def members_keyboard(member_names: list[str]):
    rows = [[KeyboardButton(name)] for name in member_names]
    rows.append([KeyboardButton("❌ Отмена")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def event_saved_actions_keyboard(include_reminder: bool = True):
    rows = []
    if include_reminder:
        rows.append([KeyboardButton("🔔 Напоминание")])
    rows.append([KeyboardButton("➕ Ещё событие"), KeyboardButton("📋 К событиям")])
    rows.append([KeyboardButton("🏠 Главное меню")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)
