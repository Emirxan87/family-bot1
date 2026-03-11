from telegram import KeyboardButton, ReplyKeyboardMarkup


def family_start_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("➕ Создать семью")],
            [KeyboardButton("🔗 Вступить по ссылке/коду")],
            [KeyboardButton("⬅️ Назад")],
        ],
        resize_keyboard=True,
    )


def family_manage_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("➕ Пригласить"), KeyboardButton("👥 Участники")],
            [KeyboardButton("✏️ Роли"), KeyboardButton("🔑 Новый код и ссылка")],
            [KeyboardButton("⬅️ Назад")],
        ],
        resize_keyboard=True,
    )


def family_role_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("👨 Папа"), KeyboardButton("👩 Мама")],
            [KeyboardButton("👧 Дочь"), KeyboardButton("👦 Сын")],
            [KeyboardButton("👵 Бабушка"), KeyboardButton("👴 Дедушка")],
            [KeyboardButton("✏️ Свое название")],
            [KeyboardButton("⬅️ Назад")],
        ],
        resize_keyboard=True,
    )


def family_member_actions_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("✏️ Изменить роль")],
            [KeyboardButton("👑 Назначить админом"), KeyboardButton("🗑 Удалить из семьи")],
            [KeyboardButton("⬅️ Назад")],
        ],
        resize_keyboard=True,
    )
