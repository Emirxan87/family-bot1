from telegram import KeyboardButton, ReplyKeyboardMarkup


EXPENSE_CATEGORIES = [
    "🛒 Еда",
    "🏠 Дом",
    "🚕 Транспорт",
    "👶 Дети",
    "💊 Здоровье",
    "🎉 Досуг",
    "💸 Долги",
    "📦 Прочее",
]

EXPENSE_OTHER_SUBCATEGORIES = [
    "👕 Одежда",
    "📱 Связь",
    "🔌 Коммуналка",
    "🚗 Авто",
    "✈️ Поездки",
    "🎁 Подарки",
    "🐾 Животные",
    "🧾 Подписки",
    "❓ Другое",
]

INCOME_CATEGORIES = [
    "💼 Зарплата",
    "💸 Подработка",
    "🎁 Подарок",
    "🔁 Возврат",
    "🏦 Проценты",
    "📦 Прочее",
]

INCOME_OTHER_SUBCATEGORIES = [
    "🪙 Премия",
    "🧑‍💻 Фриланс",
    "💳 Кэшбэк",
    "🏠 Аренда",
    "🤝 Возврат долга",
    "🏛 Выплаты",
    "❓ Другое",
]


STAT_PERIODS = {
    "📅 Сегодня": "day",
    "🗓 7 дней": "week",
    "📆 Месяц": "month",
    "📊 Квартал": "quarter",
    "📈 Год": "year",
}


def expenses_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("➖ Расход"), KeyboardButton("➕ Поступление")],
            [KeyboardButton("📊 Статистика"), KeyboardButton("📃 Последние операции")],
            [KeyboardButton("🏠 Главное меню")],
        ],
        resize_keyboard=True,
    )


def operation_type_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("➖ Расход"), KeyboardButton("➕ Поступление")],
            [KeyboardButton("⬅️ Назад"), KeyboardButton("❌ Отмена")],
        ],
        resize_keyboard=True,
    )


def categories_keyboard(operation_type: str):
    categories = EXPENSE_CATEGORIES if operation_type == "expense" else INCOME_CATEGORIES
    rows = [[KeyboardButton(categories[i]), KeyboardButton(categories[i + 1])] for i in range(0, len(categories) - 1, 2)]
    if len(categories) % 2:
        rows.append([KeyboardButton(categories[-1])])
    rows.append([KeyboardButton("⬅️ Назад"), KeyboardButton("❌ Отмена")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def other_subcategories_keyboard(operation_type: str):
    values = EXPENSE_OTHER_SUBCATEGORIES if operation_type == "expense" else INCOME_OTHER_SUBCATEGORIES
    rows = [[KeyboardButton(v)] for v in values]
    rows.append([KeyboardButton("⬅️ Назад"), KeyboardButton("❌ Отмена")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def after_save_keyboard(operation_type: str):
    add_more_text = "➕ Ещё расход" if operation_type == "expense" else "➕ Ещё поступление"
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(add_more_text), KeyboardButton("💬 Комментарий")],
            [KeyboardButton("📊 Статистика"), KeyboardButton("🏠 Главное меню")],
            [KeyboardButton("❌ Отмена")],
        ],
        resize_keyboard=True,
    )


def who_keyboard(members: list[str], include_family_shared: bool = True):
    rows = [[KeyboardButton(name)] for name in members]
    if include_family_shared:
        rows.append([KeyboardButton("👨‍👩‍👧‍👦 Общее")])
    rows.append([KeyboardButton("⬅️ Назад"), KeyboardButton("❌ Отмена")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def stats_period_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📅 Сегодня"), KeyboardButton("🗓 7 дней")],
            [KeyboardButton("📆 Месяц"), KeyboardButton("📊 Квартал")],
            [KeyboardButton("📈 Год")],
            [KeyboardButton("🏠 Главное меню"), KeyboardButton("❌ Отмена")],
        ],
        resize_keyboard=True,
    )
