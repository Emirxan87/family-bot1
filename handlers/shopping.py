import re
import unicodedata

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
    "нурофен",
    "ибупрофен",
    "парацетамол",
    "цитрамон",
    "лекарство",
    "лекарства",
    "таблетки",
    "сироп",
    "спрей",
    "капли",
    "витамины",
    "мазь",
    "бинт",
    "пластырь",
    "аптека",
    "омепразол",
    "но шпа",
    "ношпа",
    "аспирин",
    "анальгин",
}

HOUSEHOLD_KEYWORDS = {
    "порошок",
    "кондиционер",
    "отбеливатель",
    "бумага",
    "туалетная бумага",
    "салфетки",
    "губка",
    "губки",
    "мыло",
    "шампунь",
    "гель",
    "зубная паста",
    "щетка",
    "щетка",
    "средство",
    "чистящее",
    "моющее",
    "мешки",
    "пакеты",
    "фейри",
    "fairy",
}

ONLINE_KEYWORDS = {
    "ozon",
    "wb",
    "wildberries",
    "вайлдберриз",
    "алиэкспресс",
    "aliexpress",
    "amazon",
    "яндекс маркет",
    "маркетплейс",
}

EXPENSE_PREFIXES = (
    "трата ",
    "расход ",
    "потратил ",
    "потратила ",
    "заплатил ",
    "заплатила ",
)

SERVICE_RAW_TEXTS = {
    "🛒 Что купить?",
    "Что купить?",
    "➕ Добавить покупки",
    "Добавить покупки",
    "🏪 Магазин",
    "Магазин",
    "💊 Аптека",
    "Аптека",
    "📦 Онлайн",
    "Онлайн",
    "✅ Куплено",
    "Куплено",
    "🧹 Очистить купленное",
    "Очистить купленное",
    "💸 Расход",
    "Расход",
    "📖 Расходы",
    "📚 Расходы",
    "Расходы",
    "📊 Статистика",
    "Статистика",
    "💰 Итого",
    "Итого",
    "📅 Мой день",
    "Мой день",
    "👨‍👩‍👧‍👦 День семьи",
    "День семьи",
    "➕ Событие",
    "Событие",
    "ℹ️ Помощь",
    "Помощь",
    "👨‍👩‍👧‍👦 Семья",
    "Семья",
    "⬅️ Отмена",
    "Отмена",
    "🛒 Всё сразу",
    "Всё сразу",
    "Все сразу",
    "/start",
    "/help",
    "/family",
    "/join",
    "/expenses",
    "/total",
}


def canonical_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "").lower().replace("ё", "е")
    cleaned = []

    for ch in value:
        if ch.isalnum() or ch in {" ", "/", "?"}:
            cleaned.append(ch)
        else:
            cleaned.append(" ")

    value = "".join(cleaned)
    value = re.sub(r"\s+", " ", value).strip()
    return value


SERVICE_TEXTS = {canonical_text(text) for text in SERVICE_RAW_TEXTS}


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
    elif "," in text:
        parts = text.split(",")
    else:
        words = text.split()

        if len(words) >= 3:
            parts = words
        else:
            parts = [text]

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
        "waiting_for_done_items",
        "selected_done_section",
        "done_candidates",
        "waiting_for_clear_done_scope",
    ]:
        context.user_data.pop(key, None)


def is_probably_expense_text(text: str) -> bool:
    normalized = canonical_text(text)
    return any(normalized.startswith(canonical_text(prefix)) for prefix in EXPENSE_PREFIXES)


def is_service_message(text: str) -> bool:
    normalized = canonical_text(text)
    return normalized in SERVICE_TEXTS or normalized.startswith("/")


def detect_section_for_item(item: str) -> str:
    text = canonical_text(item)

    if any(word in text for word in ONLINE_KEYWORDS):
        return "📦 Маркетплейс"

    if any(word in text for word in PHARMACY_KEYWORDS):
        return "💊 Аптека"

    if any(word in text for word in HOUSEHOLD_KEYWORDS):
        return "🧴 Хозтовары"

    return "🥦 Продукты"


def parse_number_selection(text: str):
    numbers = re.findall(r"\d+", text)
    seen = set()
    result = []

    for num in numbers:
        if num in seen:
            continue
        seen.add(num)
        result.append(num)

    return result


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

    if canonical_text(text) == canonical_text("⬅️ Отмена"):
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

    if canonical_text(text) == canonical_text("⬅️ Отмена"):
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
    existing = {canonical_text(row[0]) for row in cursor.fetchall()}

    added = []
    skipped = []

    for item in items:
        key = canonical_text(item)
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
        context.user_data.get("waiting_for_done_items"),
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
            "SELECT item FROM shopping_items WHERE list_id=? AND status='active'",
            (list_id,)
        )
        existing = {canonical_text(row[0]) for row in cursor.fetchall()}

        item_key = canonical_text(item)
        target = skipped_by_section if item_key in existing else added_by_section
        target.setdefault(section, []).append(item)

        if item_key not in existing:
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

    if canonical_text(text) == canonical_text("⬅️ Отмена"):
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

    if canonical_text(text) == canonical_text("🛒 Всё сразу"):
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
        "SELECT id, item FROM shopping_items WHERE list_id=? AND status='active' ORDER BY id",
        (list_id,)
    )
    rows = cursor.fetchall()

    if not rows:
        clear_shopping_modes(context)
        await update.message.reply_text(
            f"В разделе {text} нет активных покупок",
            reply_markup=get_main_keyboard()
        )
        return True

    context.user_data["waiting_for_done_scope"] = False
    context.user_data["waiting_for_done_items"] = True
    context.user_data["selected_done_section"] = text
    context.user_data["done_candidates"] = {
        str(index): row[0] for index, row in enumerate(rows, start=1)
    }

    message_lines = [
        f"✅ Отметить купленное — {text}",
        "",
        "Отправь номер или несколько номеров.",
        "Например: 1",
        "Или: 1 3 5",
        "",
    ]

    for index, row in enumerate(rows, start=1):
        message_lines.append(f"{index}. {row[1]}")

    await update.message.reply_text(
        "\n".join(message_lines),
        reply_markup=get_cancel_keyboard()
    )
    return True


async def handle_mark_done_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_done_items"):
        return False

    text = (update.message.text or "").strip()

    if canonical_text(text) == canonical_text("⬅️ Отмена"):
        clear_shopping_modes(context)
        await update.message.reply_text(
            "Действие отменено",
            reply_markup=get_main_keyboard()
        )
        return True

    selected_numbers = parse_number_selection(text)
    done_candidates = context.user_data.get("done_candidates", {})

    if not selected_numbers:
        await update.message.reply_text(
            "Отправь номер или несколько номеров.\nНапример: 1 3",
            reply_markup=get_cancel_keyboard()
        )
        return True

    invalid_numbers = [num for num in selected_numbers if num not in done_candidates]
    if invalid_numbers:
        await update.message.reply_text(
            "Некоторые номера не найдены.\nОтправь только номера из списка.",
            reply_markup=get_cancel_keyboard()
        )
        return True

    item_ids = [done_candidates[num] for num in selected_numbers]

    placeholders = ",".join("?" for _ in item_ids)
    cursor.execute(
        f"SELECT id, item FROM shopping_items WHERE id IN ({placeholders}) ORDER BY id",
        tuple(item_ids)
    )
    rows = cursor.fetchall()

    if not rows:
        clear_shopping_modes(context)
        await update.message.reply_text(
            "Не удалось найти выбранные позиции",
            reply_markup=get_main_keyboard()
        )
        return True

    cursor.execute(
        f"UPDATE shopping_items SET status='done' WHERE id IN ({placeholders})",
        tuple(item_ids)
    )
    conn.commit()

    section = context.user_data.get("selected_done_section", "разделе")
    clear_shopping_modes(context)

    response = [f"✅ Отметил как купленные в разделе {section}:"]
    for _, item in rows:
        response.append(f"• {item}")

    await update.message.reply_text(
        "\n".join(response),
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

    if canonical_text(text) == canonical_text("⬅️ Отмена"):
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

    if canonical_text(text) == canonical_text("🛒 Всё сразу"):
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