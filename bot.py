import logging
import random
import sqlite3

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ===== ВСТАВЬ СЮДА СВОЙ ТОКЕН =====
TOKEN = "7925302773:AAHoe8mSYSVtNYL24qElXa9AcI9hI8YwsAA"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ===== БАЗА ДАННЫХ =====
conn = sqlite3.connect("family.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS families (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    family_id INTEGER,
    name TEXT,
    role TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS shopping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id INTEGER,
    item TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id INTEGER,
    amount REAL,
    description TEXT
)
""")

conn.commit()


# ===== ВСПОМОГАТЕЛЬНЫЕ =====
def get_user_family_id(telegram_id: int):
    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def parse_amount(text: str):
    parts = text.strip().split()
    if len(parts) < 2:
        return None, None

    raw = parts[0].replace(",", ".")
    try:
        amount = float(raw)
    except ValueError:
        return None, None

    description = " ".join(parts[1:]).strip()
    if amount <= 0 or not description:
        return None, None

    return amount, description


# ===== КОМАНДЫ =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    name = update.effective_user.first_name or "Участник"

    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    user = cursor.fetchone()

    if user:
        await update.message.reply_text(
            "Вы уже в семье 👍\n\n"
            "/family — участники\n"
            "/list — покупки\n"
            "/expenses — расходы\n"
            "/total — сумма\n"
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
        (telegram_id, family_id, name, "parent")
    )

    conn.commit()

    await update.message.reply_text(
        f"Семья создана 👨‍👩‍👧\n\n"
        f"Код семьи: {code}\n\n"
        f"Пусть другие напишут:\n"
        f"/join {code}"
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Напиши: /join 1234")
        return

    telegram_id = update.effective_user.id
    name = update.effective_user.first_name or "Участник"
    code = context.args[0]

    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    if cursor.fetchone():
        await update.message.reply_text("Ты уже в семье 👍")
        return

    cursor.execute("SELECT id FROM families WHERE code=?", (code,))
    fam = cursor.fetchone()

    if not fam:
        await update.message.reply_text("Семья не найдена")
        return

    family_id = fam[0]

    cursor.execute(
        "INSERT INTO users (telegram_id, family_id, name, role) VALUES (?,?,?,?)",
        (telegram_id, family_id, name, "member")
    )

    conn.commit()

    await update.message.reply_text("Ты присоединился к семье 👨‍👩‍👧")


async def family(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text("Сначала /start")
        return

    cursor.execute("SELECT name, role FROM users WHERE family_id=?", (family_id,))
    members = cursor.fetchall()

    text = "Семья:\n\n"
    for name, role in members:
        text += f"{name} — {role}\n"

    await update.message.reply_text(text)


async def add_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    text = update.message.text.strip()

    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text("Сначала /start")
        return

    cursor.execute(
        "INSERT INTO shopping (family_id, item) VALUES (?,?)",
        (family_id, text)
    )

    conn.commit()

    await update.message.reply_text(f"Добавил: {text}")


async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    cursor.execute(
        "SELECT item FROM shopping WHERE family_id=? ORDER BY id DESC",
        (family_id,)
    )

    items = cursor.fetchall()

    if not items:
        await update.message.reply_text("Список пуст")
        return

    text = "Покупки:\n\n"

    for item in items:
        text += f"• {item[0]}\n"

    await update.message.reply_text(text)


async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    text = update.message.text.strip()

    family_id = get_user_family_id(telegram_id)

    amount, description = parse_amount(text)

    if amount is None:
        await add_item(update, context)
        return

    cursor.execute(
        "INSERT INTO expenses (family_id, amount, description) VALUES (?,?,?)",
        (family_id, amount, description)
    )

    conn.commit()

    await update.message.reply_text(
        f"Расход: {amount} — {description}"
    )


async def show_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    cursor.execute(
        "SELECT amount, description FROM expenses WHERE family_id=? ORDER BY id DESC LIMIT 10",
        (family_id,)
    )

    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("Расходов нет")
        return

    text = "Последние расходы:\n\n"

    for amount, desc in rows:
        text += f"• {amount} — {desc}\n"

    await update.message.reply_text(text)


async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    cursor.execute(
        "SELECT SUM(amount) FROM expenses WHERE family_id=?",
        (family_id,)
    )

    total_sum = cursor.fetchone()[0] or 0

    await update.message.reply_text(f"Всего потрачено: {total_sum}")


# ===== ЗАПУСК =====
def main():
    if "PASTE_YOUR_TELEGRAM_BOT_TOKEN_HERE" in TOKEN:
        raise ValueError("Вставь свой токен Telegram бота в переменную TOKEN")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("family", family))
    app.add_handler(CommandHandler("list", show_list))
    app.add_handler(CommandHandler("expenses", show_expenses))
    app.add_handler(CommandHandler("total", total))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense))

    print("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
