from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
import sqlite3
import random

TOKEN = "7925302773:AAHoe8mSYSVtNYL24qElXa9AcI9hI8YwsAA"

conn = sqlite3.connect("family.db", check_same_thread=False)
cursor = conn.cursor()

# таблица семей
cursor.execute("""
CREATE TABLE IF NOT EXISTS families (
id INTEGER PRIMARY KEY AUTOINCREMENT,
code TEXT
)
""")

# таблица пользователей
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
telegram_id INTEGER,
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    telegram_id = update.message.from_user.id
    name = update.message.from_user.first_name

    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    user = cursor.fetchone()

    if user:
        await update.message.reply_text("Вы уже в семье 👍")
        return

    code = str(random.randint(1000,9999))

    cursor.execute("INSERT INTO families (code) VALUES (?)", (code,))
    family_id = cursor.lastrowid

    cursor.execute(
        "INSERT INTO users VALUES (?,?,?,?)",
        (telegram_id, family_id, name, "parent")
    )

    conn.commit()

    await update.message.reply_text(
        f"Семья создана 👨‍👩‍👧\n\n"
        f"Код семьи: {code}\n"
        f"Попросите членов семьи написать:\n"
        f"/join {code}"
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text(
            "Введите код семьи.\n\nПример:\n/join 1234"
        )
        return

    telegram_id = update.message.from_user.id
    name = update.message.from_user.first_name
    code = context.args[0]

    cursor.execute("SELECT id FROM families WHERE code=?", (code,))
    family = cursor.fetchone()

    if not family:
        await update.message.reply_text("Семья не найдена")
        return

    family_id = family[0]

    cursor.execute(
        "INSERT INTO users VALUES (?,?,?,?)",
        (telegram_id, family_id, name, "member")
    )

    conn.commit()

    await update.message.reply_text("Вы присоединились к семье 👨‍👩‍👧")


async def family(update: Update, context: ContextTypes.DEFAULT_TYPE):

    telegram_id = update.message.from_user.id

    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    family = cursor.fetchone()

    if not family:
        return

    family_id = family[0]

    cursor.execute("SELECT name, role FROM users WHERE family_id=?", (family_id,))
    members = cursor.fetchall()

    text = "Семья:\n\n"

    for m in members:

        role = "👨‍👩‍👧 родитель" if m[1]=="parent" else "👤 участник"

        text += f"{m[0]} — {role}\n"

    await update.message.reply_text(text)


async def add_item(update: Update, context: ContextTypes.DEFAULT_TYPE):

    telegram_id = update.message.from_user.id
    text = update.message.text

    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    family = cursor.fetchone()

    if not family:
        return

    family_id = family[0]

    cursor.execute(
        "INSERT INTO shopping (family_id,item) VALUES (?,?)",
        (family_id,text)
    )

    conn.commit()

    await update.message.reply_text("Добавил в список покупок")


async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):

    telegram_id = update.message.from_user.id

    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    family = cursor.fetchone()

    if not family:
        return

    family_id = family[0]

    cursor.execute("SELECT item FROM shopping WHERE family_id=?", (family_id,))
    items = cursor.fetchall()

    if not items:
        await update.message.reply_text("Список покупок пуст")
        return

    text = "Список покупок:\n\n"

    for i in items:
        text += f"{i[0]}\n"

    await update.message.reply_text(text)


async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):

    telegram_id = update.message.from_user.id
    text = update.message.text

    parts = text.split()

    if len(parts) < 2:
        await add_item(update, context)
        return

    if not parts[0].isdigit():
        await add_item(update, context)
        return

    amount = float(parts[0])
    description = " ".join(parts[1:])

    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    family = cursor.fetchone()

    if not family:
        return

    family_id = family[0]

    cursor.execute(
        "INSERT INTO expenses (family_id, amount, description) VALUES (?,?,?)",
        (family_id, amount, description)
    )

    conn.commit()

    await update.message.reply_text(f"Расход добавлен: {amount} — {description}")


async def show_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):

    telegram_id = update.message.from_user.id

    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    family = cursor.fetchone()

    if not family:
        return

    family_id = family[0]

    cursor.execute(
        "SELECT amount, description FROM expenses WHERE family_id=? ORDER BY id DESC LIMIT 10",
        (family_id,)
    )

    expenses = cursor.fetchall()

    if not expenses:
        await update.message.reply_text("Расходов пока нет")
        return

    text = "Последние расходы:\n\n"

    for e in expenses:
        text += f"{e[0]} — {e[1]}\n"

    await update.message.reply_text(text)


async def total_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):

    telegram_id = update.message.from_user.id

    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    family = cursor.fetchone()

    if not family:
        return

    family_id = family[0]

    cursor.execute(
        "SELECT SUM(amount) FROM expenses WHERE family_id=?",
        (family_id,)
    )

    total = cursor.fetchone()[0]

    if not total:
        total = 0

    await update.message.reply_text(f"Всего потрачено: {total}")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("join", join))
app.add_handler(CommandHandler("family", family))
app.add_handler(CommandHandler("list", show_list))
app.add_handler(CommandHandler("expenses", show_expenses))
app.add_handler(CommandHandler("total", total_expenses))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense))

app.run_polling()