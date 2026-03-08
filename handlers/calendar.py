from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from database import cursor, conn, get_user_family_id, get_user_name
from keyboards import get_main_keyboard, get_cancel_keyboard


def clear_calendar_modes(context: ContextTypes.DEFAULT_TYPE):
    for key in [
        "waiting_for_event_date",
        "waiting_for_event_start",
        "waiting_for_event_end",
        "waiting_for_event_title",
        "new_event_date",
        "new_event_start",
        "new_event_end",
    ]:
        context.user_data.pop(key, None)


def parse_date_input(text: str):
    text = text.strip().lower()

    if text == "сегодня":
        return datetime.now().strftime("%Y-%m-%d")

    if text == "завтра":
        return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    for fmt in ("%d.%m",):
        try:
            now = datetime.now()
            dt = datetime.strptime(text, fmt).replace(year=now.year)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def parse_time_input(text: str):
    text = text.strip()
    try:
        dt = datetime.strptime(text, "%H:%M")
        return dt.strftime("%H:%M")
    except ValueError:
        return None


def format_date_for_user(date_str: str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d.%m.%Y")
    except ValueError:
        return date_str


async def start_add_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_calendar_modes(context)
    context.user_data["waiting_for_event_date"] = True

    await update.message.reply_text(
        "Введи дату события.\n\nПримеры:\nсегодня\nзавтра\n15.03.2026",
        reply_markup=get_cancel_keyboard()
    )


async def handle_event_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_event_date"):
        return False

    text = (update.message.text or "").strip()

    if text == "⬅️ Отмена":
        clear_calendar_modes(context)
        await update.message.reply_text(
            "Добавление события отменено",
            reply_markup=get_main_keyboard()
        )
        return True

    parsed_date = parse_date_input(text)
    if not parsed_date:
        await update.message.reply_text(
            "Не понял дату.\nНапиши так:\nсегодня\nзавтра\n15.03.2026",
            reply_markup=get_cancel_keyboard()
        )
        return True

    context.user_data["new_event_date"] = parsed_date
    context.user_data["waiting_for_event_date"] = False
    context.user_data["waiting_for_event_start"] = True

    await update.message.reply_text(
        "Введи время начала.\nПример: 09:30",
        reply_markup=get_cancel_keyboard()
    )
    return True


async def handle_event_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_event_start"):
        return False

    text = (update.message.text or "").strip()

    if text == "⬅️ Отмена":
        clear_calendar_modes(context)
        await update.message.reply_text(
            "Добавление события отменено",
            reply_markup=get_main_keyboard()
        )
        return True

    parsed_time = parse_time_input(text)
    if not parsed_time:
        await update.message.reply_text(
            "Не понял время.\nНапиши так: 09:30",
            reply_markup=get_cancel_keyboard()
        )
        return True

    context.user_data["new_event_start"] = parsed_time
    context.user_data["waiting_for_event_start"] = False
    context.user_data["waiting_for_event_end"] = True

    await update.message.reply_text(
        "Введи время конца.\nПример: 11:00",
        reply_markup=get_cancel_keyboard()
    )
    return True


async def handle_event_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_event_end"):
        return False

    text = (update.message.text or "").strip()

    if text == "⬅️ Отмена":
        clear_calendar_modes(context)
        await update.message.reply_text(
            "Добавление события отменено",
            reply_markup=get_main_keyboard()
        )
        return True

    parsed_time = parse_time_input(text)
    if not parsed_time:
        await update.message.reply_text(
            "Не понял время.\nНапиши так: 11:00",
            reply_markup=get_cancel_keyboard()
        )
        return True

    start_time = context.user_data.get("new_event_start")
    if parsed_time <= start_time:
        await update.message.reply_text(
            "Время конца должно быть позже начала",
            reply_markup=get_cancel_keyboard()
        )
        return True

    context.user_data["new_event_end"] = parsed_time
    context.user_data["waiting_for_event_end"] = False
    context.user_data["waiting_for_event_title"] = True

    await update.message.reply_text(
        "Напиши название события.\nПример: Школа / Врач / Работа / Танцы",
        reply_markup=get_cancel_keyboard()
    )
    return True


async def handle_event_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_event_title"):
        return False

    text = (update.message.text or "").strip()

    if text == "⬅️ Отмена":
        clear_calendar_modes(context)
        await update.message.reply_text(
            "Добавление события отменено",
            reply_markup=get_main_keyboard()
        )
        return True

    if not text:
        await update.message.reply_text(
            "Название не должно быть пустым",
            reply_markup=get_cancel_keyboard()
        )
        return True

    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)
    member_name = get_user_name(telegram_id) or (update.effective_user.first_name or "Участник")

    if not family_id:
        clear_calendar_modes(context)
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return True

    event_date = context.user_data.get("new_event_date")
    start_time = context.user_data.get("new_event_start")
    end_time = context.user_data.get("new_event_end")

    cursor.execute(
        """
        INSERT INTO events (
            family_id,
            user_telegram_id,
            member_name,
            event_date,
            start_time,
            end_time,
            title
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (family_id, telegram_id, member_name, event_date, start_time, end_time, text)
    )
    conn.commit()

    clear_calendar_modes(context)

    await update.message.reply_text(
        f"Событие добавлено ✅\n\n"
        f"{format_date_for_user(event_date)}\n"
        f"{start_time}–{end_time}\n"
        f"{text}",
        reply_markup=get_main_keyboard()
    )
    return True


async def show_my_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        """
        SELECT event_date, start_time, end_time, title
        FROM events
        WHERE user_telegram_id=? AND event_date=?
        ORDER BY start_time
        """,
        (telegram_id, today)
    )
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text(
            "На сегодня у тебя событий нет",
            reply_markup=get_main_keyboard()
        )
        return

    text = "📅 Мой день:\n\n"
    for event_date, start_time, end_time, title in rows:
        text += f"• {start_time}–{end_time} — {title}\n"

    await update.message.reply_text(
        text,
        reply_markup=get_main_keyboard()
    )


async def show_family_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)
    today = datetime.now().strftime("%Y-%m-%d")

    if not family_id:
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return

    cursor.execute(
        """
        SELECT member_name, start_time, end_time, title
        FROM events
        WHERE family_id=? AND event_date=?
        ORDER BY member_name, start_time
        """,
        (family_id, today)
    )
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text(
            "На сегодня в семье событий нет",
            reply_markup=get_main_keyboard()
        )
        return

    grouped = {}
    for member_name, start_time, end_time, title in rows:
        grouped.setdefault(member_name, []).append((start_time, end_time, title))

    text = "👨‍👩‍👧 День семьи:\n\n"
    for member_name, items in grouped.items():
        text += f"{member_name}\n"
        for start_time, end_time, title in items:
            text += f"• {start_time}–{end_time} — {title}\n"
        text += "\n"

    await update.message.reply_text(
        text.strip(),
        reply_markup=get_main_keyboard()
    )
