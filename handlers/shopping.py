from telegram import Update
from telegram.ext import ContextTypes

from keyboards.main_menu import main_menu_keyboard
from keyboards.shopping import items_inline, lists_inline, shopping_menu_keyboard
from messages import NEED_FAMILY
from repos.shopping_repo import ShoppingRepo
from repos.states_repo import StatesRepo
from repos.users_repo import UsersRepo
from services.activity_service import ActivityService
from services.notification_service import NotificationService
from services.shopping_service import ShoppingService
from states import ADDING_SHOPPING_ITEM, SELECTING_SHOPPING_LIST

users_repo = UsersRepo()
states_repo = StatesRepo()
shopping_service = ShoppingService()
shopping_repo = ShoppingRepo()
activity_service = ActivityService()
notify_service = NotificationService()


async def shopping_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Покупки 🛒", reply_markup=shopping_menu_keyboard())


async def shopping_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    user = users_repo.get_user(user_id)
    if not user or not user["family_id"]:
        await update.message.reply_text(NEED_FAMILY, reply_markup=main_menu_keyboard())
        return
    family_id = user["family_id"]

    state, payload = states_repo.get_state(user_id)
    if state == SELECTING_SHOPPING_LIST:
        try:
            list_id = int(text)
        except ValueError:
            await update.message.reply_text("Выберите список через кнопки ниже.")
            return
        states_repo.set_state(user_id, ADDING_SHOPPING_ITEM, {"list_id": list_id})
        await update.message.reply_text("Отправьте название товара:")
        return

    if state == ADDING_SHOPPING_ITEM:
        list_id = payload.get("list_id")
        if not list_id:
            states_repo.clear_state(user_id)
            await update.message.reply_text("Сессия устарела, начните заново.")
            return
        item_id = shopping_service.add_item(list_id, text, user_id)
        item = shopping_repo.get_item_by_id(item_id)
        activity_service.log(family_id, user_id, "shopping_add", f"добавил(а) товар: {text}")
        await notify_service.notify_family(
            context.bot,
            family_id,
            user_id,
            f"🛒 {user['full_name']} добавил(а) в «{item['list_name']}»: {text}",
        )
        await update.message.reply_text("Добавлено ✅", reply_markup=shopping_menu_keyboard())
        return

    if text == "📋 Мои списки":
        lists = shopping_service.lists(family_id)
        await update.message.reply_text("Выберите список:", reply_markup=lists_inline(lists))
    elif text == "➕ Добавить товар":
        lists = shopping_service.lists(family_id)
        await update.message.reply_text("Сначала выберите список:", reply_markup=lists_inline(lists))
        states_repo.set_state(user_id, ADDING_SHOPPING_ITEM, {})
    elif text == "🏠 Главное меню":
        await update.message.reply_text("Главное меню", reply_markup=main_menu_keyboard())
