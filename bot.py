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

# =========================
# НАСТРОЙКИ
# =========================
TOKEN = "7925302773:AAHoe8mSYSVtNYL24qElXa9AcI9hI8YwsAA"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# =========================
# БАЗА ДАННЫХ
# =========================
conn = sqlite3.connect("family.db", check_same_thread=False)
cursor = conn.cursor()

# семьи
cursor.execute("""
CREATE TABLE IF NOT EXISTS families (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE
)
""")

# пользователи
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    family_id INTEGER,
    name TEXT,
    role TEXT
)
""")

# покупки
cursor.execute("""
CREATE TABLE IF NOT EXISTS shopping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id INTEGER,
    item TEXT
)
""")

# расходы
cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id INTEGER,
    amount REAL,
    description TEXT
)
""")

conn.commit()


# =========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================
def get_user_family_id(telegram_id: int):
    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def parse_amount(text: str):
    """
    Примеры:
    '250 молоко'
    '99.90 хлеб'
    '99,90 хлеб'
    """
    parts = text.strip().split()

    if len(parts) < 2:
        return None, None

    raw_amount = parts[0].replace(",", ".")

    try:
        amount = float(raw_amount)
    except ValueError:
        return None, None

    description = " ".join(parts[1:]).strip()

    if amount <= 0 or not description:
        return None, None

    return amount, description


# =========================
# КОМАНДЫ
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    name = update.effective_user.first_name or "Участник"

    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    user = cursor.fetchone()

    if user:
        await update.message.reply_text(
            "Вы уже в семье 👍\n\n"
            "Команды:\n"
            "/family — показать семью\n"
            "/list — список покупок\n"
            "/expenses — последние расходы\n"
            "/total — сумма расходов\n"
            "/help — помощь"
        )
        return

    code = str(random.randint(1000, 9999))

    # на случай совпадения кода
    while True:
        cursor.execute("SELECT id FROM families WHERE code=?", (code,))
        exists = cursor.fetchone()
        if not exists:
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
        "Семья создана 👨‍👩‍👧\n\n"
        f"Код семьи: {code}\n\n"
        "Попросите членов семьи написать:\n"
        f"/join {code}\n\n"
        "Полезные команды:\n"
        "/family — показать состав семьи\n"
        "/list — список покупок\n"
        "/expenses — последние расходы\n"
        "/total — общая сумма расходов"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Команды:\n\n"
        "/start — создать семью\n"
        "/join 1234 — присоединиться к семье\n"
        "/family — показать участников\n"
        "/list — показать список покупок\n"
        "/expenses — последние 10 расходов\n"
        "/total — сумма всех расходов\n\n"
        "Как пользоваться:\n"
        "1. Напиши обычный текст: молоко\n"
        "   → добавится в список покупок\n\n"
        "2. Напиши: 250 молоко\n"
        "   → добавится расход 250 и описание 'молоко'"
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Введите код семьи.\n\nПример:\n/join 1234"
        )
        return

    telegram_id = update.effective_user.id
    name = update.effective_user.first_name or "Участник"
    code = context.args[0].strip()

    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    existing_user = cursor.fetchone()

    if existing_user:
        await update.message.reply_text("Вы уже состоите в семье 👍")
        return

    cursor.execute("SELECT id FROM families WHERE code=?", (code,))
    family = cursor.fetchone()

    if not family:
        await update.message.reply_text("Семья не найдена")
        return

    family_id = family[0]

    cursor.execute(
        "INSERT INTO users (telegram_id, family_id, name, role) VALUES (?,?,?,?)",
        (telegram_id, family_id, name, "member")
    )

    conn.commit()

    await update.message.reply_text("Вы присоединились к семье 👨‍👩‍👧")


async def family(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text(
            "Вы ещё не в семье.\nСначала напишите /start или /join код"
        )
        return

    cursor.execute("SELECT name, role FROM users WHERE family_id=?", (family_id,))
    members = cursor.fetchall()

    text = "Семья:\n\n"

    for name, role in members:
        role_text = "👨‍👩‍👧 родитель" if role == "parent" else "👤 участник"
        text += f"{name} — {role_text}\n"

    await update.message.reply_text(text)


async def add_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    text = (update.message.text or "").strip()

    if not text:
        return

    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text(
            "Сначала нужно создать семью через /start или войти через /join код"
        )
        return

    cursor.execute(
        "INSERT INTO shopping (family_id, item) VALUES (?, ?)",
        (family_id, text)
    )

    conn.commit()

    await update.message.reply_text(f"Добавил в список покупок: {text}")


async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text(
            "Сначала нужно создать семью через /start или войти через /join код"
        )
        return

    cursor.execute("SELECT item FROM shopping WHERE family_id=? ORDER BY id DESC", (family_id,))
    items = cursor.fetchall()

    if not items:
        await update.message.reply_text("Список покупок пуст")
        return

    text = "Список покупок:\n\n"
    for item in items:
        text += f"• {item[0]}\n"

    await update.message.reply_text(text)


async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    text = (update.message.text or "").strip()

    if not text:
        return

    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text(
            "Сначала нужно создать семью через /start или войти через /join код"
        )
        return

    amount, description = parse_amount(text)

    # если первое слово не число — считаем это покупкой
    if amount is None:
        await add_item(update, context)
        return

    cursor.execute(
        "INSERT INTO expenses (family_id, amount, description) VALUES (?, ?, ?)",
        (family_id, amount, description)
    )

    conn.commit()

    await update.message.reply_text(
        f"Расход добавлен: {amount:.2f} — {description}"
    )


async def show_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text(
            "Сначала нужно создать семью через /start или войти через /join код"
        )
        return

    cursor.execute(
        "SELECT amount, description FROM expenses WHERE family_id=? ORDER BY id DESC LIMIT 10",
        (family_id,)
    )
    expenses = cursor.fetchall()

    if not expenses:
        await update.message.reply_text("Расходов пока нет")
        return

    text = "Последние расходы:\n\n"
    for amount, description in expenses:
        text += f"• {amount:.2f} — {description}\n"

    await update.message.reply_text(text)


async def total_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text(
            "Сначала нужно создать семью через /start или войти через /join код"
        )
        return

    cursor.execute(
        "SELECT SUM(amount) FROM expenses WHERE family_id=?",
        (family_id,)
    )
    total = cursor.fetchone()[0]

    if total is None:
        total = 0

    await update.message.reply_text(f"Всего потрачено: {total:.2f}")


# =========================
# ЗАПУСК БОТА
# =========================
def main():
    if TOKEN == "7925302773:AAHoe8mSYSVtNYL24qElXa9AcI9hI8YwsAA":
        raise ValueError("Сначала вставь TOKEN в переменную TOKEN")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("family", family))
    app.add_handler(CommandHandler("list", show_list))
    app.add_handler(CommandHandler("expenses", show_expenses))
    app.add_handler(CommandHandler("total", total_expenses))

    # Любой обычный текст:
    # - "молоко" -> покупка
    # - "250 молоко" -> расход
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
