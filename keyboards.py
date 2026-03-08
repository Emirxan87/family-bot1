from telegram import ReplyKeyboardMarkup

SHOPPING_LISTS = [
    "🥦 Продукты",
    "💊 Аптека",
    "🧴 Хозтовары",
    "📦 Маркетплейс",
    "📌 Другое",
]

EXPENSE_CATEGORIES = [
    "🍎 Еда",
    "🚕 Транспорт",
    "👶 Дети",
    "🏠 Дом",
    "💊 Здоровье",
    "🎉 Развлечения",
    "📦 Другое",
]


def get_main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🛒 Что купить?", "➕ Добавить покупки"],
            ["🏪 Магазин", "💊 Аптека", "📦 Онлайн"],
            ["✅ Куплено", "🧹 Очистить купленное"],
            ["💸 Расход", "📖 Расходы"],
            ["📊 Статистика", "💰 Итого"],
            ["📅 Мой день", "👨‍👩‍👧 День семьи"],
            ["➕ Событие", "ℹ️ Помощь"],
            ["👨‍👩‍👧 Семья"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def get_shopping_section_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🥦 Продукты", "💊 Аптека"],
            ["🧴 Хозтовары", "📦 Маркетплейс"],
            ["📌 Другое"],
            ["⬅️ Отмена"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def get_done_scope_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🥦 Продукты", "💊 Аптека"],
            ["🧴 Хозтовары", "📦 Маркетплейс"],
            ["📌 Другое", "🛒 Всё сразу"],
            ["⬅️ Отмена"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def get_expense_category_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🍎 Еда", "🚕 Транспорт"],
            ["👶 Дети", "🏠 Дом"],
            ["💊 Здоровье", "🎉 Развлечения"],
            ["📦 Другое"],
            ["⬅️ Отмена"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        [["⬅️ Отмена"]],
        resize_keyboard=True,
        is_persistent=True,
    )
