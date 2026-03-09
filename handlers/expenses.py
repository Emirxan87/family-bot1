from telegram import Update
from telegram.ext import ContextTypes

from keyboards.expenses import expenses_menu_keyboard
from keyboards.main_menu import main_menu_keyboard
from repos.states_repo import StatesRepo
from repos.users_repo import UsersRepo
from services.activity_service import ActivityService
from services.expense_service import ExpenseService
from services.notification_service import NotificationService
from states import ADDING_EXPENSE_AMOUNT, ADDING_EXPENSE_CATEGORY

users_repo = UsersRepo()
states_repo = StatesRepo()
expense_service = ExpenseService()
activity_service = ActivityService()
notify_service = NotificationService()


async def expenses_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Расходы 💰", reply_markup=expenses_menu_keyboard())


async def expenses_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    user = users_repo.get_user(user_id)
    if not user or not user["family_id"]:
        await update.message.reply_text("Сначала присоединитесь к семье.", reply_markup=main_menu_keyboard())
        return

    state, payload = states_repo.get_state(user_id)

    if text == "➕ Добавить расход":
        states_repo.set_state(user_id, ADDING_EXPENSE_AMOUNT, {})
        await update.message.reply_text("Введите сумму (например 350.50):")
    elif text == "📃 Последние расходы":
        await update.message.reply_text(expense_service.latest_text(user["family_id"]))
    elif text == "📊 Сводка":
        await update.message.reply_text(expense_service.summary_text(user["family_id"]))
    elif text == "🏠 Главное меню":
        await update.message.reply_text("Главное меню", reply_markup=main_menu_keyboard())
    elif state == ADDING_EXPENSE_AMOUNT:
        try:
            amount = float(text.replace(",", "."))
        except ValueError:
            await update.message.reply_text("Не вижу сумму. Введите число, например 450")
            return
        payload["amount"] = amount
        states_repo.set_state(user_id, ADDING_EXPENSE_CATEGORY, payload)
        await update.message.reply_text("Введите категорию (Продукты, Транспорт, Дом и т.д.):")
    elif state == ADDING_EXPENSE_CATEGORY:
        amount = float(payload["amount"])
        expense_service.add_expense(user["family_id"], user_id, amount, text, "")
        states_repo.clear_state(user_id)
        activity_service.log(user["family_id"], user_id, "expense_add", f"добавил(а) расход {amount:.2f} ₽")
        await notify_service.notify_family(
            context.bot,
            user["family_id"],
            user_id,
            f"💰 {user['full_name']} добавил(а) расход: {amount:.2f} ₽ ({text})",
        )
        await update.message.reply_text("Расход сохранён ✅", reply_markup=expenses_menu_keyboard())
