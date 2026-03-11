from telegram import Update
from telegram.ext import ContextTypes

from keyboards.shopping import items_inline, shopping_list_actions_keyboard
from repos.shopping_repo import ShoppingRepo
from repos.states_repo import StatesRepo
from repos.users_repo import UsersRepo
from services.activity_service import ActivityService
from services.notification_service import NotificationService
from services.shopping_service import ShoppingService

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

    if data.startswith("shop:list:"):
        list_id = int(data.split(":")[-1])
        items = shopping_service.get_visible_items(list_id)
        states_repo.set_state(user_id, "shopping_selected_list", {"list_id": list_id})
        await query.message.reply_text(
            shopping_service.render_list(list_id), reply_markup=items_inline(items)
        )
        await query.message.reply_text(
            "Управление списком:",
            reply_markup=shopping_list_actions_keyboard(),
        )
        return

    if data.startswith("shop:toggle:") and user and user["family_id"]:
        item_id = int(data.split(":")[-1])
        item = shopping_service.toggle_item(item_id, user_id)
        if not item:
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
            f"🛍 {user['full_name']} {status} «{item['title']}»",
        )
        return
