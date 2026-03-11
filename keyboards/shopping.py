from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def shopping_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🛒 Что купить"), KeyboardButton("📋 Мои списки")],
            [KeyboardButton("➕ Добавить товар")],
            [KeyboardButton("🏠 В меню")],
        ],
        resize_keyboard=True,
    )


def shopping_list_actions_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("➕ Добавить товар"), KeyboardButton("✅ Отметить всё купленным")],
            [KeyboardButton("♻️ Вернуть всё в активные"), KeyboardButton("🧹 Очистить купленные")],
            [KeyboardButton("🗑 Очистить список")],
            [KeyboardButton("🛒 Что купить"), KeyboardButton("📋 Мои списки")],
            [KeyboardButton("❌ Отмена"), KeyboardButton("🏠 В меню")],
        ],
        resize_keyboard=True,
    )


def shopping_family_actions_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("✅ Отметить всё купленным"), KeyboardButton("✅ Отметить несколько")],
            [KeyboardButton("➕ Добавить товар"), KeyboardButton("📋 Открыть списки")],
            [KeyboardButton("↩ Назад"), KeyboardButton("🏠 В меню")],
        ],
        resize_keyboard=True,
    )


def shopping_bulk_actions_keyboard(selected_count: int):
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(f"✅ Готово ({selected_count})"), KeyboardButton("✅ Отметить всё купленным")],
            [KeyboardButton("❌ Отмена"), KeyboardButton("🛒 Что купить")],
        ],
        resize_keyboard=True,
    )


def shopping_confirm_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("✅ Подтвердить"), KeyboardButton("❌ Отмена")],
            [KeyboardButton("📋 Мои списки"), KeyboardButton("🏠 В меню")],
        ],
        resize_keyboard=True,
    )


def lists_inline(lists):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(lst["name"], callback_data=f"shop:list:{lst['id']}")] for lst in lists]
    )


def items_inline(items):
    rows = []
    for item in items:
        label = ("✅ " if item["is_done"] else "⬜ ") + item["display_title"]
        rows.append([InlineKeyboardButton(label[:64], callback_data=f"shop:toggle:{item['id']}")])
    return InlineKeyboardMarkup(rows or [[InlineKeyboardButton("Пусто", callback_data="noop")]])


def family_items_inline(items):
    rows = []
    for item in items:
        label = f"✅ {item['display_title']}"
        rows.append([InlineKeyboardButton(label[:64], callback_data=f"shop:family_done:{item['id']}")])
    return InlineKeyboardMarkup(rows or [[InlineKeyboardButton("Список пуст", callback_data="noop")]])


def family_bulk_inline(items, selected_ids):
    rows = []
    selected = set(selected_ids or [])
    for item in items:
        mark = "☑️" if item["id"] in selected else "⬜"
        label = f"{mark} {item['display_title']} · {item['list_name']}"
        rows.append([InlineKeyboardButton(label[:64], callback_data=f"shop:bulk_pick:{item['id']}")])
    if not rows:
        rows = [[InlineKeyboardButton("Список пуст", callback_data="noop")]]
    return InlineKeyboardMarkup(rows)
