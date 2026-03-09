from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def shopping_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📋 Мои списки"), KeyboardButton("➕ Добавить товар")],
            [KeyboardButton("🏠 Главное меню")],
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
        label = ("✅ " if item["is_done"] else "⬜ ") + item["title"]
        rows.append([InlineKeyboardButton(label[:64], callback_data=f"shop:toggle:{item['id']}")])
    return InlineKeyboardMarkup(rows or [[InlineKeyboardButton("Пусто", callback_data="noop")]])
