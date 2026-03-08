import re

from telegram import Update
from telegram.ext import ContextTypes

from database import cursor, conn, get_user_family_id, get_list_id
from keyboards import (
    SHOPPING_LISTS,
    get_main_keyboard,
    get_shopping_section_keyboard,
    get_done_scope_keyboard,
    get_cancel_keyboard,
)


PHARMACY_KEYWORDS = {
    "нурофен", "ибупрофен", "парацетамол", "цитрамон", "лекарство",
    "лекарства", "таблетки", "сироп", "спрей", "капли", "витамины",
    "мазь", "бинт", "пластырь", "аптека", "омепразол", "но-шпа",
    "ношпа", "аспирин", "анальгин",
}

HOUSEHOLD_KEYWORDS = {
    "порошок", "кондиционер", "отбеливатель", "бумага", "туалетная бумага",
    "салфетки", "губка", "губки", "мыло", "шампунь", "гель", "зубная паста",
    "щетка", "щётка", "средство", "чистящее", "моющее", "мешки", "пакеты",
    "фейри", "fairy",
}

ONLINE_KEYWORDS = {
    "ozon", "wb", "wildberries", "вайлдберриз", "алиэкспресс", "aliexpress",
    "amazon", "яндекс маркет", "маркетплейс",
}

EXPENSE_PREFIXES = (
    "трата ",
    "расход ",
    "потратил ",
    "потратила ",
    "заплатил ",
    "заплатила ",
)


def clean_item_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^[\-\•\*\–\—]+\s*", "", text)
    text = re.sub(r"^\d+[\.\)]\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ,;.")


def split_shopping_items(raw_text: str):
    text = raw_text.strip()

    if "\n" in text:
        parts = text.splitlines()
    else:
        parts = text.split(",")

    result = []
    seen = set()

    for part in parts:
        item = clean_item_text(part)
        if not item:
            continue

        key = item.lower()
        if key in seen:
            continue

        seen.add(key)
        result.append(item)

    return result


def format_grouped_shopping_rows(rows):
    grouped = {}
    for list_name, item in rows:
        grouped.setdefault(list_name, []).append(item)

    text_parts = ["🛒 Нужно купить:\n"]
    total = 0

    for section in SHOPPING_LISTS:
        items = grouped.get(section, [])
        if not items:
            continue

        total += len(items)
        text_parts.append(f"{section} — {len(items)}")
        for item in items:
            text_parts.append(f"• {item}")
        text_parts.append("")

    if total == 0:
        return "Список покупок пуст"

    return "\n".join(text_parts).strip()


def clear_shopping_modes(context: ContextTypes.DEFAULT_TYPE):
    for key in [
        "waiting_for_shopping_section",
        "waiting_for_shopping_items",
        "selected_shopping_section",
        "waiting_for_done_scope",
        "waiting_for_clear_done_scope",
    ]:
        context.user_data.pop(key, None)


def is_probably_expense_text(text: str) -> bool:
    lower_text = text.strip().lower()
    return any(lower_text.startswith(prefix) for prefix in EXPENSE_PREFIXES)


def is_service_message(text: str) -> bool:
    normalized = text.strip().lower()

    blocked_exact = {
        "что купить?",
        "➕ добавить покупки",
        "магазин",
        "аптека",
        "онлайн",
        "✅ куплено",
        "очистить купленное",
        "расход",
        "расходы",
        "статистика",
        "итого",
        "мой день",
        "день семьи",
        "➕ событие",
        "семья",
        "ℹ️ помощь",
        "⬅️ отмена",
        "/start",
        "/help",
        "/family",
        "/join",
        "/expenses",
        "/total",
    }

    return normalized in blocked_exact or normalized.startswith("/")


def detect_section_for_item(item: str) -> str:
    text = item.lower()

    if any(word in text for word in ONLINE_KEYWORDS):
        return "📦 Маркетплейс"

    if any(word in text for word in PHARMACY_KEYWORDS):
        return "💊 Аптека"

    if any(word in text for word in HOUSEHOLD_KEYWORDS):
        return "🧴 Хозтовары"

    return "🥦 Продукты"


async def show_all_shopping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return

    cursor.execute(
        """
        SELECT sl.name, si.item
        FROM shopping_items si
        JOIN shopping_lists sl ON sl.id = si.list_id
        WHERE sl.family_id=? AND si.status='active'
        ORDER BY sl.id, si.id
        """,
        (family_id,)
    )
    rows = cursor.fetchall()

    await update.message.reply_text(
        format_grouped_shopping_rows(rows),
        reply_markup=get_main_keyboard()
    )


async def show_store_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return

    cursor.execute(
        """
        SELECT sl.name, si.item
        FROM shopping_items si
        JOIN shopping_lists sl ON sl.id = si.list_id
        WHERE sl.family_id=? AND si.status='active' AND sl.name IN (?, ?)
        ORDER BY sl.id, si.id
        """,
        (family_id, "🥦 Продукты", "🧴 Хозтовары")
    )
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text(
            "Для магазина список пуст",
            reply_markup=get_main_keyboard()
        )
        return

    grouped = {}
    for list_name, item in rows:
        grouped.setdefault(list_name, []).append(item)

    text = "🏪 Купить в магазине:\n\n"
    for section in ["🥦 Продукты", "🧴 Хозтовары"]:
        items = grouped.get(section, [])
        if not items:
            continue
        text += f"{section}\n"
        for item in items:
            text += f"• {item}\n"
        text += "\n"

    await update.message.reply_text(
        text.strip(),
        reply_markup=get_main_keyboard()
    )


async def show_section(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    section_name: str,
    title: str
):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return

    list_id = get_list_id(family_id, section_name)

    cursor.execute(
        "SELECT item FROM shopping_items WHERE list_id=? AND status='active' ORDER BY id",
        (list_id,)
    )
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text(
            f"{title}: список пуст",
            reply_markup=get_main_keyboard()
        )
        return

    text = f"{title}:\n\n"
    for row in rows:
        text += f"• {row[0]}\n"

    await update.message.reply_text(
        text,
        reply_markup=get_main_keyboard()
    )


async def show_pharmacy_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_section(update, context, "💊 Аптека", "💊 Купить в аптеке")


async def show_online_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_section(update, context, "📦 Маркетплейс", "📦 Заказать онлайн")


async def start_add_shopping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_shopping_modes(context)
    context.user_data["waiting_for_shopping_section"] = True

    await update.message.reply_text(
        "Выбери раздел, куда добавить покупки:",
        reply_markup=get_shopping_section_keyboard()
    )


async def handle_shopping_section_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_shopping_section"):
        return False

    text = (update.message.text or "").strip()

    if text == "⬅️ Отмена":
        clear_shopping_modes(context)
        await update.message.reply_text(
            "Действие отменено",
            reply_markup=get_main_keyboard()
        )
        return True

    if text not in SHOPPING_LISTS:
        await update.message.reply_text(
            "Выбери раздел кнопкой ниже",
            reply_markup=get_shopping_section_keyboard()
        )
        return True

    context.user_data["waiting_for_shopping_section"] = False
    context.user_data["waiting_for_shopping_items"] = True
    context.user_data["selected_shopping_section"] = text

    await update.message.reply_text(
        f"Раздел выбран: {text}\n\n"
        f"Теперь отправь покупки одним сообщением.\n\n"
        f"Можно так:\n"
        f"молоко\nхлеб\nяйца\n\n"
        f"или так:\n"
        f"молоко, хлеб, яйца",
        reply_markup=get_cancel_keyboard()
    )
    return True


async def handle_shopping_items_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_shopping_items"):
        return False

    text = (update.message.text or "").strip()

    if text == "⬅️ Отмена":
        clear_shopping_modes(context)
        await update.message.reply_text(
            "Действие отменено",
            reply_markup=get_main_keyboard()
        )
        return True

    items = split_shopping_items(text)
    if not items:
        await update.message.reply_text(
            "Не получилось распознать покупки.\nОтправь список ещё раз.",
            reply_markup=get_cancel_keyboard()
        )
        return True

    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        clear_shopping_modes(context)
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return True

    section = context.user_data.get("selected_shopping_section")
    list_id = get_list_id(family_id, section)

    cursor.execute(
        "SELECT item FROM shopping_items WHERE list_id=? AND status='active'",
        (list_id,)
    )
    existing = {row[0].strip().lower() for row in cursor.fetchall()}

    added = []
    skipped = []

    for item in items:
        key = item.lower()
        if key in existing:
            skipped.append(item)
            continue

        cursor.execute(
            "INSERT INTO shopping_items (list_id, item, status) VALUES (?, ?, 'active')",
            (list_id, item)
        )
        existing.add(key)
        added.append(item)

    conn.commit()
    clear_shopping_modes(context)

    response = [f"Добавление в раздел {section}:\n"]
    if added:
        response.append(f"Добавил {len(added)}:")
        for item in added:
            response.append(f"• {item}")
        response.append("")

    if skipped:
        response.append("Уже были в списке:")
        for item in skipped:
            response.append(f"• {item}")

    await update.message.reply_text(
        "\n".join(response).strip(),
        reply_markup=get_main_keyboard()
    )
    return True


async def handle_quick_shopping_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if any([
        context.user_data.get("waiting_for_shopping_section"),
        context.user_data.get("waiting_for_shopping_items"),
        context.user_data.get("waiting_for_done_scope"),
        context.user_data.get("waiting_for_clear_done_scope"),
        context.user_data.get("waiting_for_expense_category"),
        context.user_data.get("waiting_for_expense_input"),
        context.user_data.get("waiting_for_event_date"),
        context.user_data.get("waiting_for_event_start"),
        context.user_data.get("waiting_for_event_end"),
        context.user_data.get("waiting_for_event_title"),
    ]):
        return False

    text = (update.message.text or "").strip()
    if not text:
        return False

    if is_service_message(text):
        return False

    if is_probably_expense_text(text):
        return False

    items = split_shopping_items(text)
    if not items:
        return False

    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)
    if not family_id:
        return False

    added_by_section = {}
    skipped_by_section = {}

    for item in items:
        section = detect_section_for_item(item)
        list_id = get_list_id(family_id, section)

        cursor.execute(
            "SELECT 1 FROM shopping_items WHERE list_id=? AND status='active' AND LOWER(TRIM(item))= ?",
            (list_id, item.strip().lower())
        )
        exists = cursor.fetchone()

        target = skipped_by_section if exists else added_by_section
        target.setdefault(section, []).append(item)

        if not exists:
            cursor.execute(
                "INSERT INTO shopping_items (list_id, item, status) VALUES (?, ?, 'active')",
                (list_id, item)
            )

    if not added_by_section and not skipped_by_section:
        return False

    conn.commit()

    response = ["🛒 Добавил в покупки:\n"]

    for section in SHOPPING_LISTS:
        section_items = added_by_section.get(section, [])
        if not section_items:
            continue
        response.append(section)
        for item in section_items:
            response.append(f"• {item}")
        response.append("")

    if skipped_by_section:
        response.append("Уже были в списке:")
        for section in SHOPPING_LISTS:
            section_items = skipped_by_section.get(section, [])
            if not section_items:
                continue
            response.append(section)
            for item in section_items:
                response.append(f"• {item}")
            response.append("")

    await update.message.reply_text(
        "\n".join(response).strip(),
        reply_markup=get_main_keyboard()
    )
    return True


async def start_mark_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_shopping_modes(context)
    context.user_data["waiting_for_done_scope"] = True

    await update.message.reply_text(
        "Что отметить купленным?",
        reply_markup=get_done_scope_keyboard()
    )


async def handle_mark_done_scope(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_done_scope"):
        return False

    text = (update.message.text or "").strip()
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if text == "⬅️ Отмена":
        clear_shopping_modes(context)
        await update.message.reply_text(
            "Действие отменено",
            reply_markup=get_main_keyboard()
        )
        return True

    if not family_id:
        clear_shopping_modes(context)
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return True

    if text == "🛒 Всё сразу":
        cursor.execute(
            """
            UPDATE shopping_items
            SET status='done'
            WHERE id IN (
                SELECT si.id
                FROM shopping_items si
                JOIN shopping_lists sl ON sl.id = si.list_id
                WHERE sl.family_id=? AND si.status='active'
            )
            """,
            (family_id,)
        )
        conn.commit()
        clear_shopping_modes(context)
        await update.message.reply_text(
            "Все активные покупки отмечены как купленные ✅",
            reply_markup=get_main_keyboard()
        )
        return True

    if text not in SHOPPING_LISTS:
        await update.message.reply_text(
            "Выбери раздел кнопкой ниже",
            reply_markup=get_done_scope_keyboard()
        )
        return True

    list_id = get_list_id(family_id, text)
    cursor.execute(
        "UPDATE shopping_items SET status='done' WHERE list_id=? AND status='active'",
        (list_id,)
    )
    conn.commit()
    clear_shopping_modes(context)

    await update.message.reply_text(
        f"Все покупки в разделе {text} отмечены как купленные ✅",
        reply_markup=get_main_keyboard()
    )
    return True


async def start_clear_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_shopping_modes(context)
    context.user_data["waiting_for_clear_done_scope"] = True

    await update.message.reply_text(
        "Что очистить из уже купленного?",
        reply_markup=get_done_scope_keyboard()
    )


async def handle_clear_done_scope(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_clear_done_scope"):
        return False

    text = (update.message.text or "").strip()
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if text == "⬅️ Отмена":
        clear_shopping_modes(context)
        await update.message.reply_text(
            "Действие отменено",
            reply_markup=get_main_keyboard()
        )
        return True

    if not family_id:
        clear_shopping_modes(context)
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return True

    if text == "🛒 Всё сразу":
        cursor.execute(
            """
            DELETE FROM shopping_items
            WHERE id IN (
                SELECT si.id
                FROM shopping_items si
                JOIN shopping_lists sl ON sl.id = si.list_id
                WHERE sl.family_id=? AND si.status='done'
            )
            """,
            (family_id,)
        )
        conn.commit()
        clear_shopping_modes(context)
        await update.message.reply_text(
            "Все купленные позиции очищены 🧹",
            reply_markup=get_main_keyboard()
        )
        return True

    if text not in SHOPPING_LISTS:
        await update.message.reply_text(
            "Выбери раздел кнопкой ниже",
            reply_markup=get_done_scope_keyboard()
        )
        return True

    list_id = get_list_id(family_id, text)
    cursor.execute(
        "DELETE FROM shopping_items WHERE list_id=? AND status='done'",
        (list_id,)
    )
    conn.commit()
    clear_shopping_modes(context)

    await update.message.reply_text(
        f"Купленные позиции из раздела {text} очищены 🧹",
        reply_markup=get_main_keyboard()
    )
    return True
