from telegram import Update
from telegram.ext import ContextTypes

from keyboards.shopping import (
    family_bulk_inline,
    family_items_inline,
    items_inline,
    shopping_bulk_actions_keyboard,
    shopping_family_actions_keyboard,
    shopping_list_actions_keyboard,
)
from repos.shopping_repo import ShoppingRepo
from repos.states_repo import StatesRepo
from repos.users_repo import UsersRepo
from services.activity_service import ActivityService
from services.notification_service import NotificationService
from services.shopping_service import ShoppingService
from utils.display_name import preferred_display_name

shopping_service = ShoppingService()
shopping_repo = ShoppingRepo()
users_repo = UsersRepo()
states_repo = StatesRepo()
activity_service = ActivityService()
notify_service = NotificationService()


async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    user_id = query.from_user.id
    user = users_repo.get_user(user_id)

    if not user or not user["family_id"]:
        await query.message.reply_text("Сначала присоединитесь к семье.")
        return
    family_id = user["family_id"]

    if data.startswith("shop:list:"):
        try:
            list_id = int(data.split(":")[-1])
        except ValueError:
            await query.message.reply_text("Не удалось открыть список. Обновите экран.")
            return
        if not shopping_service.list_belongs_to_family(list_id, family_id):
            await query.message.reply_text("Этот список недоступен.")
            return
        items = shopping_service.get_visible_items(list_id)
        states_repo.set_state(user_id, "shopping_selected_list", {"list_id": list_id})
        await query.message.reply_text(
            shopping_service.render_list(list_id), reply_markup=items_inline(items)
        )
        await query.message.reply_text(
            "Что дальше?",
            reply_markup=shopping_list_actions_keyboard(),
        )
        return

    if data.startswith("shop:toggle:"):
        try:
            item_id = int(data.split(":")[-1])
        except ValueError:
            await query.message.reply_text("Эта кнопка устарела. Обновите список.")
            return
        item = shopping_service.toggle_family_item(family_id, item_id, user_id)
        if not item:
            await query.message.reply_text("Товар не найден или уже недоступен.")
            return
        list_items = shopping_service.get_visible_items(item["list_id"])
        await query.message.edit_text(
            shopping_service.render_list(item["list_id"]), reply_markup=items_inline(list_items)
        )
        status = "купил(а)" if item["is_done"] else "вернул(а) в список"
        details = f"{status}: {item['title']}"
        activity_service.log(item["family_id"], user_id, "shopping_toggle", details)
        await notify_service.notify_family(
            context.bot,
            item["family_id"],
            user_id,
            f"🛍 {preferred_display_name(user)} {status} «{item['title']}»",
        )
        return

    if data.startswith("shop:family_done:"):
        try:
            item_id = int(data.split(":")[-1])
        except ValueError:
            await query.message.reply_text("Эта кнопка устарела. Откройте раздел заново.")
            return
        changed = shopping_service.mark_family_item_done(family_id, item_id, user_id)
        items = shopping_service.family_active_items(family_id)
        await query.message.edit_text(
            shopping_service.render_family_active_items(family_id),
            reply_markup=family_items_inline(items),
        )
        if changed:
            item = shopping_repo.get_item_by_id(item_id)
            if item:
                activity_service.log(
                    family_id,
                    user_id,
                    "shopping_toggle",
                    f"купил(а): {item['title']}",
                )
                await notify_service.notify_family(
                    context.bot,
                    family_id,
                    user_id,
                    f"🛍 {preferred_display_name(user)} купил(а) «{item['title']}»",
                )
        await query.message.reply_text("Что дальше?", reply_markup=shopping_family_actions_keyboard())
        return

    if data.startswith("shop:bulk_pick:"):
        try:
            item_id = int(data.split(":")[-1])
        except ValueError:
            await query.message.reply_text("Эта кнопка устарела. Откройте раздел заново.")
            return
        state, payload = states_repo.get_state(user_id)
        if state != "shopping_family_bulk":
            payload = {"selected_ids": []}
        payload = payload or {"selected_ids": []}
        selected_ids = set(payload.get("selected_ids") or [])

        active_ids = {i["id"] for i in shopping_service.family_active_items(family_id)}
        if item_id not in active_ids:
            selected_ids.discard(item_id)
        elif item_id in selected_ids:
            selected_ids.remove(item_id)
        else:
            selected_ids.add(item_id)

        selected_list = sorted(selected_ids)
        states_repo.set_state(user_id, "shopping_family_bulk", {"selected_ids": selected_list})
        items = shopping_service.family_active_items(family_id)
        await query.message.edit_text(
            "Выберите несколько товаров:",
            reply_markup=family_bulk_inline(items, selected_list),
        )
        await query.message.reply_text(
            f"Выбрано: {len(selected_list)}",
            reply_markup=shopping_bulk_actions_keyboard(len(selected_list)),
        )
        return

    await query.message.reply_text("Кнопка устарела. Откройте раздел заново.")
