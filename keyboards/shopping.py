from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

BTN_SHOPPING_SECTION = "🛒 Покупки"
BTN_SHOPPING_HOME = "🛒 Что купить"
BTN_MY_LISTS = "📋 Мои списки"
BTN_OPEN_LISTS = "📋 Открыть списки"
BTN_ADD_ITEM = "➕ Добавить товар"
BTN_ADD_MORE = "✅ Добавить ещё"
BTN_OPEN_LIST = "📖 Открыть список"
BTN_NEW_LIST = "🆕 Новый список"
BTN_MARK_ALL_DONE = "✅ Отметить всё купленным"
BTN_MARK_MANY = "✅ Отметить несколько"
BTN_RESTORE_ALL = "♻️ Вернуть всё в активные"
BTN_CLEAR_DONE = "🧹 Очистить купленные"
BTN_CLEAR_LIST = "🗑 Очистить список"
BTN_BACK = "⬅️ Назад"
BTN_BACK_TO_FAMILY = "↩ Назад"
BTN_CANCEL = "❌ Отмена"
BTN_CONFIRM = "✅ Подтвердить"
BTN_MAIN_MENU_SHORT = "🏠 В меню"
BTN_MAIN_MENU_FULL = "🏠 Главное меню"


def shopping_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_SHOPPING_HOME), KeyboardButton(BTN_MY_LISTS)],
            [KeyboardButton(BTN_ADD_ITEM)],
            [KeyboardButton(BTN_MAIN_MENU_SHORT)],
        ],
        resize_keyboard=True,
    )


def shopping_list_actions_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_ADD_ITEM), KeyboardButton(BTN_MARK_ALL_DONE)],
            [KeyboardButton(BTN_RESTORE_ALL), KeyboardButton(BTN_CLEAR_DONE)],
            [KeyboardButton(BTN_CLEAR_LIST)],
            [KeyboardButton(BTN_SHOPPING_HOME), KeyboardButton(BTN_MY_LISTS)],
            [KeyboardButton(BTN_CANCEL), KeyboardButton(BTN_MAIN_MENU_SHORT)],
        ],
        resize_keyboard=True,
    )


def shopping_family_actions_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_MARK_ALL_DONE), KeyboardButton(BTN_MARK_MANY)],
            [KeyboardButton(BTN_ADD_ITEM), KeyboardButton(BTN_OPEN_LISTS)],
            [KeyboardButton(BTN_BACK_TO_FAMILY), KeyboardButton(BTN_MAIN_MENU_SHORT)],
        ],
        resize_keyboard=True,
    )


def shopping_bulk_actions_keyboard(selected_count: int):
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(f"✅ Готово ({selected_count})"), KeyboardButton(BTN_MARK_ALL_DONE)],
            [KeyboardButton(BTN_CANCEL), KeyboardButton(BTN_SHOPPING_HOME)],
        ],
        resize_keyboard=True,
    )


def shopping_confirm_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_CONFIRM), KeyboardButton(BTN_CANCEL)],
            [KeyboardButton(BTN_MY_LISTS), KeyboardButton(BTN_MAIN_MENU_SHORT)],
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
