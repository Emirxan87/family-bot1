import random

from telegram import Update
from telegram.ext import ContextTypes

from database import cursor, conn, ensure_default_lists, get_user_family_id
from keyboards import get_main_keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    name = update.effective_user.first_name or "Участник"

    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    user = cursor.fetchone()

    if user:
        ensure_default_lists(user[0])
        await update.message.reply_text(
            "Вы уже в семье 👍",
            reply_markup=get_main_keyboard()
        )
        return

    code = str(random.randint(1000, 9999))
    while True:
        cursor.execute("SELECT id FROM families WHERE code=?", (code,))
        if not cursor.fetchone():
            break
        code = str(random.randint(1000, 9999))

    cursor.execute("INSERT INTO families (code) VALUES (?)", (code,))
    family_id = cursor.lastrowid

    cursor.execute(
        "INSERT INTO users (telegram_id, family_id, name, role) VALUES (?,?,?,?)",
        (telegram_id, family_id, name, "родитель")
    )
    conn.commit()

    ensure_default_lists(family_id)

    await update.message.reply_text(
        f"Семья создана 👨‍👩‍👧\n\n"
        f"Код семьи: {code}\n\n"
        f"Пусть остальные напишут:\n"
        f"/join {code}",
        reply_markup=get_main_keyboard()
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Напиши так:\n/join 1234",
            reply_markup=get_main_keyboard()
        )
        return

    code = context.args[0].strip()
    telegram_id = update.effective_user.id
    name = update.effective_user.first_name or "Участник"

    cursor.execute("SELECT id FROM families WHERE code=?", (code,))
    fam = cursor.fetchone()

    if not fam:
        await update.message.reply_text(
            "Семья не найдена",
            reply_markup=get_main_keyboard()
        )
        return

    family_id = fam[0]

    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    existing_user = cursor.fetchone()

    if existing_user:
        old_family_id = existing_user[0]

        if old_family_id == family_id:
            await update.message.reply_text(
                "Ты уже в этой семье 👍",
                reply_markup=get_main_keyboard()
            )
            return

        cursor.execute(
            """
            UPDATE users
            SET family_id=?, name=?, role=?
            WHERE telegram_id=?
            """,
            (family_id, name, "участник", telegram_id)
        )
        conn.commit()

        ensure_default_lists(family_id)

        await update.message.reply_text(
            "Ты перешёл в эту семью 👨‍👩‍👧",
            reply_markup=get_main_keyboard()
        )
        return

    cursor.execute(
        "INSERT INTO users (telegram_id, family_id, name, role) VALUES (?,?,?,?)",
        (telegram_id, family_id, name, "участник")
    )
    conn.commit()

    ensure_default_lists(family_id)

    await update.message.reply_text(
        "Вы присоединились к семье 👨‍👩‍👧",
        reply_markup=get_main_keyboard()
    )


async def family(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return

    cursor.execute(
        "SELECT name, role FROM users WHERE family_id=? ORDER BY name",
        (family_id,)
    )
    members = cursor.fetchall()

    text = "👨‍👩‍👧 Семья:\n\n"
    for name, role in members:
        text += f"• {name} — {role}\n"

    await update.message.reply_text(
        text,
        reply_markup=get_main_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ Как пользоваться:\n\n"
        "Покупки:\n"
        "1. Нажми ➕ Добавить покупки\n"
        "2. Выбери раздел\n"
        "3. Отправь список одним сообщением\n\n"
        "Расходы:\n"
        "1. Нажми 💸 Расход\n"
        "2. Выбери категорию\n"
        "3. Напиши: 250 молоко\n\n"
        "Календарь:\n"
        "1. Нажми ➕ Событие\n"
        "2. Введи дату\n"
        "3. Введи начало и конец\n"
        "4. Напиши название события"
    )

    await update.message.reply_text(
        text,
        reply_markup=get_main_keyboard()
    )
