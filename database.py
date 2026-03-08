import os
import sqlite3

# путь к базе данных
DB_PATH = os.getenv("DB_PATH", "/data/family.db")

# подключение к базе
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()


def init_db():

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
    CREATE TABLE IF NOT EXISTS shopping_lists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER,
        name TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shopping_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        list_id INTEGER,
        item TEXT,
        status TEXT DEFAULT 'active'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER,
        amount REAL,
        category TEXT,
        description TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER,
        user_telegram_id INTEGER,
        member_name TEXT,
        event_date TEXT,
        start_time TEXT,
        end_time TEXT,
        title TEXT
    )
    """)

    conn.commit()


def get_user_family_id(telegram_id: int):

    cursor.execute(
        "SELECT family_id FROM users WHERE telegram_id=?",
        (telegram_id,)
    )

    row = cursor.fetchone()

    return row[0] if row else None


def get_user_name(telegram_id: int):

    cursor.execute(
        "SELECT name FROM users WHERE telegram_id=?",
        (telegram_id,)
    )

    row = cursor.fetchone()

    return row[0] if row else None


def ensure_default_lists(family_id: int):

    default_lists = [
        "🥦 Продукты",
        "💊 Аптека",
        "🧴 Хозтовары",
        "📦 Маркетплейс",
        "📌 Другое",
    ]

    for list_name in default_lists:

        cursor.execute(
            "SELECT id FROM shopping_lists WHERE family_id=? AND name=?",
            (family_id, list_name)
        )

        if not cursor.fetchone():

            cursor.execute(
                "INSERT INTO shopping_lists (family_id, name) VALUES (?, ?)",
                (family_id, list_name)
            )

    conn.commit()


def get_list_id(family_id: int, list_name: str):

    ensure_default_lists(family_id)

    cursor.execute(
        "SELECT id FROM shopping_lists WHERE family_id=? AND name=?",
        (family_id, list_name)
    )

    row = cursor.fetchone()

    return row[0] if row else None
