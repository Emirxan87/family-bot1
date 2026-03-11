from telegram import KeyboardButton, ReplyKeyboardMarkup


EXPENSE_CATEGORIES = [
    "🛒 Продукты",
    "🏠 Дом",
    "🚕 Транспорт",
    "👶 Дети",
    "💊 Здоровье",
    "☕ Кафе",
    "🎉 Развлечения",
    "📦 Прочее",
]

EXPENSE_OTHER_SUBCATEGORIES = [
    "👕 Одежда",
    "💄 Красота и уход",
    "🐾 Животные",
    "📚 Образование",
    "🎁 Подарки",
    "📱 Связь и интернет",
    "🔌 Коммунальные",
    "🚗 Авто",
    "✈️ Путешествия",
    "💼 Работа",
    "🧾 Подписки",
    "🏛 Налоги и платежи",
    "❓ Не подходит ни под одну",
]

INCOME_CATEGORIES = [
    "💼 Зарплата",
    "💸 Подработка",
    "🎁 Подарок",
    "🔁 Возврат",
    "🛍 Продажа",
    "📦 Прочее",
]

INCOME_OTHER_SUBCATEGORIES = [
    "🪙 Премия",
    "🧑‍💻 Фриланс",
    "💳 Кэшбэк",
    "🏦 Проценты / вклад",
    "🏠 Аренда / пассивный доход",
    "🤝 Возврат долга",
    "🏛 Соцвыплаты",
    "👨‍👩‍👧 Перевод в семью",
    "❓ Не подходит ни под одну",
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
    who_text = "👤 Кто потратил" if operation_type == "expense" else "👤 Кто получил"
    add_more_text = "➕ Ещё расход" if operation_type == "expense" else "➕ Ещё поступление"
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(who_text), KeyboardButton("💬 Комментарий")],
            [KeyboardButton(add_more_text), KeyboardButton("📊 Статистика")],
            [KeyboardButton("🏠 Главное меню"), KeyboardButton("❌ Отмена")],
        ],
        resize_keyboard=True,
    )


def who_keyboard(members: list[str], include_family_shared: bool = True):
    rows = [[KeyboardButton(name)] for name in members]
    if include_family_shared:
        rows.append([KeyboardButton("👨‍👩‍👧 Общее")])
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
