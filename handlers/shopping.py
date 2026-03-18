from telegram import Update
from telegram.ext import ContextTypes

from keyboards.main_menu import main_menu_keyboard
from keyboards.shopping import (
    family_bulk_inline,
    family_items_inline,
    items_inline,
    lists_inline,
    shopping_bulk_actions_keyboard,
    shopping_confirm_keyboard,
    shopping_family_actions_keyboard,
    shopping_list_actions_keyboard,
    shopping_menu_keyboard,
)
from messages import NEED_FAMILY
from repos.shopping_repo import ShoppingRepo
from repos.states_repo import StatesRepo
from repos.users_repo import UsersRepo
from services.activity_service import ActivityService
from services.notification_service import NotificationService
from services.shopping_service import ShoppingService
from states import ADDING_SHOPPING_ITEM
from utils.display_name import preferred_display_name

users_repo = UsersRepo()
states_repo = StatesRepo()
shopping_service = ShoppingService()
shopping_repo = ShoppingRepo()
activity_service = ActivityService()
notify_service = NotificationService()

SHOPPING_SYSTEM_BUTTONS = {
    "🛒 Покупки",
    "🛒 Что купить",
    "📅 Календарь",
    "💰 Расходы",
    "📸 Моменты",
    "👨‍👩‍👧‍👦 Семья",
    "⚙️ Ещё",
    "🏠 В меню",
    "🏠 Главное меню",
    "📋 Мои списки",
    "📋 Открыть списки",
    "➕ Добавить товар",
    "✅ Отметить всё купленным",
    "✅ Отметить несколько",
    "✅ Готово (0)",
    "♻️ Вернуть всё в активные",
    "🧹 Очистить купленные",
    "🗑 Очистить список",
    "⬅️ Назад",
    "↩ Назад",
    "❌ Отмена",
    "✅ Подтвердить",
    "✅ Добавить ещё",
    "📖 Открыть список",
    "🆕 Новый список",
}

CONFIRM_MARK_ALL_DONE = "mark_all_done"
CONFIRM_CLEAR_LIST = "clear_list"


async def _show_list_screen(update: Update, list_id: int):
    items = shopping_service.get_visible_items(list_id)
    await update.message.reply_text(
        shopping_service.render_list(list_id),
        reply_markup=items_inline(items),
    )
    await update.message.reply_text(
        "Что дальше?",
        reply_markup=shopping_list_actions_keyboard(),
    )


async def _show_family_screen(update: Update, family_id: int):
    items = shopping_service.family_active_items(family_id)
    await update.message.reply_text(
        shopping_service.render_family_active_items(family_id),
        reply_markup=family_items_inline(items),
    )
    await update.message.reply_text(
        "Можно быстро закрыть покупки.",
        reply_markup=shopping_family_actions_keyboard(),
    )


async def _show_bulk_screen(update: Update, family_id: int, selected_ids: list[int]):
    items = shopping_service.family_active_items(family_id)
    selected_existing = [i["id"] for i in items if i["id"] in set(selected_ids or [])]
    await update.message.reply_text(
        "Выберите несколько товаров:",
        reply_markup=family_bulk_inline(items, selected_existing),
    )
    await update.message.reply_text(
        f"Выбрано: {len(selected_existing)}",
        reply_markup=shopping_bulk_actions_keyboard(len(selected_existing)),
    )


async def _open_lists(update: Update, family_id: int):
    lists = shopping_service.lists(family_id)
    await update.message.reply_text("Выберите список:", reply_markup=lists_inline(lists))


async def _request_list_for_list_action(update: Update, family_id: int, action_title: str):
    await update.message.reply_text(
        f"Чтобы выполнить «{action_title}», сначала выберите список 👇",
        reply_markup=lists_inline(shopping_service.lists(family_id)),
    )


def _is_valid_family_list(list_id: int | None, family_id: int) -> bool:
    return bool(list_id and shopping_service.list_belongs_to_family(list_id, family_id))


async def shopping_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Покупки 🛒", reply_markup=shopping_menu_keyboard())


async def shopping_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        return

    user_id = update.effective_user.id
    user = users_repo.get_user(user_id)
    if not user or not user["family_id"]:
        await update.message.reply_text(NEED_FAMILY, reply_markup=main_menu_keyboard())
        return
    family_id = user["family_id"]

    state, payload = states_repo.get_state(user_id)
    payload = payload or {}

    is_system_button = text in SHOPPING_SYSTEM_BUTTONS or text.startswith("✅ Готово (")

    if state == ADDING_SHOPPING_ITEM and is_system_button:
        selected_list_id = payload.get("list_id") if payload else None
        if selected_list_id:
            states_repo.set_state(user_id, "shopping_selected_list", {"list_id": selected_list_id})
            state, payload = "shopping_selected_list", {"list_id": selected_list_id}
        else:
            states_repo.clear_state(user_id)
            state, payload = None, {}

    if text in {"📋 Мои списки", "📋 Открыть списки", "🆕 Новый список"}:
        states_repo.clear_state(user_id)
        await _open_lists(update, family_id)
        return

    if text in {"🛒 Что купить", "↩ Назад"}:
        states_repo.set_state(user_id, "shopping_family_view", {})
        await _show_family_screen(update, family_id)
        return

    if text in {"❌ Отмена", "⬅️ Назад"}:
        states_repo.clear_state(user_id)
        await update.message.reply_text("Ок 👌", reply_markup=shopping_menu_keyboard())
        return

    if text in {"🏠 В меню", "🏠 Главное меню"}:
        states_repo.clear_state(user_id)
        await update.message.reply_text("Главное меню", reply_markup=main_menu_keyboard())
        return

    selected_list_id = payload.get("list_id")

    if text in {"➕ Добавить товар", "✅ Добавить ещё"}:
        if _is_valid_family_list(selected_list_id, family_id):
            states_repo.set_state(user_id, ADDING_SHOPPING_ITEM, {"list_id": selected_list_id})
            await update.message.reply_text("Напишите товар одним сообщением.")
            await update.message.reply_text("Можно отправить сразу следующий товар.", reply_markup=shopping_list_actions_keyboard())
        else:
            if selected_list_id:
                states_repo.set_state(user_id, "shopping_selected_list", {})
            await update.message.reply_text("Сначала выберите список:", reply_markup=lists_inline(shopping_service.lists(family_id)))
        return

    if text == "📖 Открыть список":
        if not _is_valid_family_list(selected_list_id, family_id):
            if selected_list_id:
                states_repo.set_state(user_id, "shopping_selected_list", {})
            await update.message.reply_text("Сначала выберите список:", reply_markup=lists_inline(shopping_service.lists(family_id)))
            return
        states_repo.set_state(user_id, "shopping_selected_list", {"list_id": selected_list_id})
        await _show_list_screen(update, selected_list_id)
        return

    if state == ADDING_SHOPPING_ITEM:
        list_id = payload.get("list_id")
        if not _is_valid_family_list(list_id, family_id):
            states_repo.clear_state(user_id)
            await update.message.reply_text("Список не выбран. Нажмите «📋 Мои списки».", reply_markup=shopping_menu_keyboard())
            return

        item_id = shopping_service.add_item(list_id, text, user_id)
        if not item_id:
            await update.message.reply_text("Не понял товар. Напишите короче, например: Молоко")
            return

        item = shopping_repo.get_item_by_id(item_id)
        activity_service.log(family_id, user_id, "shopping_add", f"добавил(а) товар: {item['title']}")
        await notify_service.notify_family(
            context.bot,
            family_id,
            user_id,
            f"🛒 {preferred_display_name(user)} добавил(а) в «{item['list_name']}»: {item['title']}",
        )
        states_repo.set_state(user_id, ADDING_SHOPPING_ITEM, {"list_id": list_id})
        await update.message.reply_text("Добавил ✅ Что дальше?\n• Ещё товар\n• Открыть список\n• В меню")
        await _show_list_screen(update, list_id)
        return

    if text == "✅ Отметить несколько":
        states_repo.set_state(user_id, "shopping_family_bulk", {"selected_ids": []})
        await _show_bulk_screen(update, family_id, [])
        return

    if state == "shopping_family_bulk" and text.startswith("✅ Готово"):
        selected_ids = payload.get("selected_ids") or []
        changed = shopping_service.mark_family_items_done(family_id, selected_ids, user_id)
        await update.message.reply_text(f"Готово ✅ Отметил: {changed}")
        states_repo.set_state(user_id, "shopping_family_view", {})
        await _show_family_screen(update, family_id)
        return

    if text == "✅ Отметить всё купленным":
        if state in {"shopping_family_view", "shopping_family_bulk"}:
            changed = shopping_service.mark_all_family_done(family_id, user_id)
            await update.message.reply_text(f"Готово ✅ Закрыл все покупки: {changed}")
            states_repo.set_state(user_id, "shopping_family_view", {})
            await _show_family_screen(update, family_id)
            return
        if not _is_valid_family_list(selected_list_id, family_id):
            if selected_list_id:
                states_repo.set_state(user_id, "shopping_selected_list", {})
            await _request_list_for_list_action(update, family_id, "✅ Отметить всё купленным")
            return
        states_repo.set_state(
            user_id,
            "shopping_confirm_action",
            {"list_id": selected_list_id, "action": CONFIRM_MARK_ALL_DONE},
        )
        await update.message.reply_text("Отметить весь список купленным?", reply_markup=shopping_confirm_keyboard())
        return

    if text == "🗑 Очистить список":
        if not _is_valid_family_list(selected_list_id, family_id):
            if selected_list_id:
                states_repo.set_state(user_id, "shopping_selected_list", {})
            await _request_list_for_list_action(update, family_id, "🗑 Очистить список")
            return
        states_repo.set_state(
            user_id,
            "shopping_confirm_action",
            {"list_id": selected_list_id, "action": CONFIRM_CLEAR_LIST},
        )
        await update.message.reply_text("Удалить все товары из списка?", reply_markup=shopping_confirm_keyboard())
        return

    if state == "shopping_confirm_action" and text == "✅ Подтвердить":
        action = payload.get("action")
        list_id = payload.get("list_id")
        if not _is_valid_family_list(list_id, family_id):
            states_repo.clear_state(user_id)
            await update.message.reply_text("Сессия устарела.", reply_markup=shopping_menu_keyboard())
            return

        if action == CONFIRM_MARK_ALL_DONE:
            changed = shopping_service.mark_all_done(list_id, user_id)
            await update.message.reply_text(f"Готово ✅ Отметил: {changed}")
        elif action == CONFIRM_CLEAR_LIST:
            changed = shopping_service.clear_list(list_id)
            await update.message.reply_text(f"Готово ✅ Удалил: {changed}")

        states_repo.set_state(user_id, "shopping_selected_list", {"list_id": list_id})
        await _show_list_screen(update, list_id)
        return

    if text == "♻️ Вернуть всё в активные":
        if not _is_valid_family_list(selected_list_id, family_id):
            if selected_list_id:
                states_repo.set_state(user_id, "shopping_selected_list", {})
            await _request_list_for_list_action(update, family_id, "♻️ Вернуть всё в активные")
            return
        changed = shopping_service.restore_all_active(selected_list_id)
        await update.message.reply_text(f"Готово ✅ Вернул: {changed}")
        states_repo.set_state(user_id, "shopping_selected_list", {"list_id": selected_list_id})
        await _show_list_screen(update, selected_list_id)
        return

    if text == "🧹 Очистить купленные":
        if not _is_valid_family_list(selected_list_id, family_id):
            if selected_list_id:
                states_repo.set_state(user_id, "shopping_selected_list", {})
            await _request_list_for_list_action(update, family_id, "🧹 Очистить купленные")
            return
        changed = shopping_service.clear_done(selected_list_id)
        await update.message.reply_text(f"Готово ✅ Удалил купленные: {changed}")
        states_repo.set_state(user_id, "shopping_selected_list", {"list_id": selected_list_id})
        await _show_list_screen(update, selected_list_id)
        return

    await update.message.reply_text("Нажмите кнопку ниже 👇", reply_markup=shopping_menu_keyboard())
