from telegram import Update
from telegram.ext import ContextTypes

from keyboards.main_menu import main_menu_keyboard
from keyboards.shopping import (
    items_inline,
    lists_inline,
    shopping_confirm_keyboard,
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
from utils.display_name import preferred_display_name
from states import ADDING_SHOPPING_ITEM

users_repo = UsersRepo()
states_repo = StatesRepo()
shopping_service = ShoppingService()
shopping_repo = ShoppingRepo()
activity_service = ActivityService()
notify_service = NotificationService()

SHOPPING_SYSTEM_BUTTONS = {
    "🛒 Покупки",
    "📅 Календарь",
    "💰 Расходы",
    "📸 Моменты",
    "👨‍👩‍👧‍👦 Семья",
    "⚙️ Ещё",
    "🏠 Главное меню",
    "📋 Мои списки",
    "➕ Добавить товар",
    "✅ Отметить всё купленным",
    "♻️ Вернуть всё в активные",
    "🧹 Очистить купленные",
    "🗑 Очистить список",
    "⬅️ Назад",
    "❌ Отмена",
    "✅ Подтвердить",
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
        "Управление списком:",
        reply_markup=shopping_list_actions_keyboard(),
    )


async def _open_lists(update: Update, family_id: int):
    lists = shopping_service.lists(family_id)
    await update.message.reply_text("Выберите список:", reply_markup=lists_inline(lists))


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

    if state == ADDING_SHOPPING_ITEM and text in SHOPPING_SYSTEM_BUTTONS:
        states_repo.clear_state(user_id)
        state, payload = None, {}

    if text == "📋 Мои списки":
        await _open_lists(update, family_id)
        return

    if text in {"❌ Отмена", "⬅️ Назад"}:
        states_repo.clear_state(user_id)
        await update.message.reply_text("Ок, действие отменено.", reply_markup=shopping_menu_keyboard())
        return

    if text == "🏠 Главное меню":
        states_repo.clear_state(user_id)
        await update.message.reply_text("Главное меню", reply_markup=main_menu_keyboard())
        return

    if state == ADDING_SHOPPING_ITEM:
        list_id = payload.get("list_id")
        if not list_id:
            states_repo.clear_state(user_id)
            await update.message.reply_text("Сессия устарела, начните заново.")
            return

        item_id = shopping_service.add_item(list_id, text, user_id)
        if not item_id:
            await update.message.reply_text("Название товара пустое или служебное. Отправьте другой текст.")
            return

        item = shopping_repo.get_item_by_id(item_id)
        activity_service.log(family_id, user_id, "shopping_add", f"добавил(а) товар: {item['title']}")
        await notify_service.notify_family(
            context.bot,
            family_id,
            user_id,
            f"🛒 {preferred_display_name(user)} добавил(а) в «{item['list_name']}»: {item['title']}",
        )
        await update.message.reply_text("Добавлено ✅ Отправьте ещё товар или нажмите «❌ Отмена».")
        await _show_list_screen(update, list_id)
        return

    if text == "➕ Добавить товар":
        selected_list_id = payload.get("list_id") if payload else None
        if selected_list_id:
            states_repo.set_state(user_id, ADDING_SHOPPING_ITEM, {"list_id": selected_list_id})
            await update.message.reply_text(
                "Режим добавления включён. Отправляйте товары по одному.",
                reply_markup=shopping_list_actions_keyboard(),
            )
        else:
            await update.message.reply_text("Сначала выберите список:", reply_markup=lists_inline(shopping_service.lists(family_id)))
        return

    selected_list_id = payload.get("list_id") if payload else None

    if text == "✅ Отметить всё купленным":
        if not selected_list_id:
            await update.message.reply_text("Сначала откройте нужный список через «📋 Мои списки».")
            return
        states_repo.set_state(
            user_id,
            "shopping_confirm_action",
            {"list_id": selected_list_id, "action": CONFIRM_MARK_ALL_DONE},
        )
        await update.message.reply_text(
            "Подтвердите: отметить ВСЕ товары купленными?",
            reply_markup=shopping_confirm_keyboard(),
        )
        return

    if text == "🗑 Очистить список":
        if not selected_list_id:
            await update.message.reply_text("Сначала откройте нужный список через «📋 Мои списки».")
            return
        states_repo.set_state(
            user_id,
            "shopping_confirm_action",
            {"list_id": selected_list_id, "action": CONFIRM_CLEAR_LIST},
        )
        await update.message.reply_text(
            "Подтвердите: удалить ВСЕ товары из списка?",
            reply_markup=shopping_confirm_keyboard(),
        )
        return

    if state == "shopping_confirm_action" and text == "✅ Подтвердить":
        action = payload.get("action")
        list_id = payload.get("list_id")
        if not list_id:
            states_repo.clear_state(user_id)
            await update.message.reply_text("Сессия устарела.", reply_markup=shopping_menu_keyboard())
            return

        if action == CONFIRM_MARK_ALL_DONE:
            changed = shopping_service.mark_all_done(list_id, user_id)
            await update.message.reply_text(f"Готово ✅ Отмечено: {changed}")
        elif action == CONFIRM_CLEAR_LIST:
            changed = shopping_service.clear_list(list_id)
            await update.message.reply_text(f"Готово ✅ Удалено: {changed}")

        states_repo.set_state(user_id, "shopping_selected_list", {"list_id": list_id})
        await _show_list_screen(update, list_id)
        return

    if text == "♻️ Вернуть всё в активные":
        if not selected_list_id:
            await update.message.reply_text("Сначала откройте нужный список через «📋 Мои списки».")
            return
        changed = shopping_service.restore_all_active(selected_list_id)
        await update.message.reply_text(f"Готово ✅ Возвращено: {changed}")
        states_repo.set_state(user_id, "shopping_selected_list", {"list_id": selected_list_id})
        await _show_list_screen(update, selected_list_id)
        return

    if text == "🧹 Очистить купленные":
        if not selected_list_id:
            await update.message.reply_text("Сначала откройте нужный список через «📋 Мои списки».")
            return
        changed = shopping_service.clear_done(selected_list_id)
        await update.message.reply_text(f"Готово ✅ Удалено купленных: {changed}")
        states_repo.set_state(user_id, "shopping_selected_list", {"list_id": selected_list_id})
        await _show_list_screen(update, selected_list_id)
