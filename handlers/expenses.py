from telegram import Update
from telegram.ext import ContextTypes

from keyboards.expenses import (
    EXPENSE_CATEGORIES,
    EXPENSE_OTHER_SUBCATEGORIES,
    INCOME_CATEGORIES,
    INCOME_OTHER_SUBCATEGORIES,
    STAT_PERIODS,
    after_save_keyboard,
    categories_keyboard,
    expenses_menu_keyboard,
    other_subcategories_keyboard,
    stats_period_keyboard,
    who_keyboard,
)
from keyboards.main_menu import main_menu_keyboard
from repos.states_repo import StatesRepo
from repos.users_repo import UsersRepo
from services.activity_service import ActivityService
from services.expense_service import ExpenseService
from utils.display_name import preferred_display_name
from states import (
    ADDING_EXPENSE_ACTOR,
    ADDING_EXPENSE_AMOUNT,
    ADDING_EXPENSE_CATEGORY,
    ADDING_EXPENSE_COMMENT,
    ADDING_EXPENSE_SUBCATEGORY,
)

users_repo = UsersRepo()
states_repo = StatesRepo()
expense_service = ExpenseService()
activity_service = ActivityService()


async def expenses_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Финансы 💳", reply_markup=expenses_menu_keyboard())


async def expenses_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    user = users_repo.get_user(user_id)
    if not user or not user["family_id"]:
        await update.message.reply_text("Сначала присоединитесь к семье.", reply_markup=main_menu_keyboard())
        return

    state, payload = states_repo.get_state(user_id)

    if text in {"❌ Отмена", "🏠 Главное меню"}:
        states_repo.clear_state(user_id)
        if text == "🏠 Главное меню":
            await update.message.reply_text("Главное меню", reply_markup=main_menu_keyboard())
        else:
            await update.message.reply_text("Ок, отменил 👌", reply_markup=expenses_menu_keyboard())
        return

    if text == "⬅️ Назад":
        await _handle_back(update, user_id, state, payload)
        return

    if text == "📃 Последние операции":
        await update.message.reply_text(expense_service.latest_text(user["family_id"]), reply_markup=expenses_menu_keyboard())
        return

    if text == "📊 Статистика":
        states_repo.clear_state(user_id)
        await update.message.reply_text("Выберите период:", reply_markup=stats_period_keyboard())
        return

    if text in STAT_PERIODS:
        await update.message.reply_text(
            expense_service.stats_text(user["family_id"], STAT_PERIODS[text]),
            reply_markup=expenses_menu_keyboard(),
        )
        return

    if text in {"➖ Расход", "➕ Поступление", "➕ Ещё расход", "➕ Ещё поступление"}:
        operation_type = "income" if "Поступление" in text else "expense"
        states_repo.set_state(user_id, ADDING_EXPENSE_CATEGORY, {"operation_type": operation_type})
        prompt = "Выберите категорию расхода:" if operation_type == "expense" else "Выберите категорию поступления:"
        await update.message.reply_text(prompt, reply_markup=categories_keyboard(operation_type))
        return

    if text == "💬 Комментарий" and payload.get("last_operation_id"):
        states_repo.set_state(user_id, ADDING_EXPENSE_COMMENT, payload)
        await update.message.reply_text("Напишите комментарий к последней операции:")
        return

    if text in {"👤 Кто потратил", "👤 Кто получил"} and payload.get("last_operation_id"):
        await _ask_actor(update, user_id, user["family_id"], payload)
        return

    if state == ADDING_EXPENSE_CATEGORY:
        await _handle_category(update, user_id, text, payload)
        return

    if state == ADDING_EXPENSE_SUBCATEGORY:
        await _handle_subcategory(update, user_id, text, payload)
        return

    if state == ADDING_EXPENSE_AMOUNT:
        await _handle_amount(update, user, text, payload)
        return

    if state == ADDING_EXPENSE_COMMENT:
        comment = text.strip()
        if comment:
            expense_service.update_comment(payload["last_operation_id"], user["family_id"], comment)
            await update.message.reply_text("Комментарий добавлен ✅", reply_markup=after_save_keyboard(payload["operation_type"]))
        else:
            await update.message.reply_text("Пустой комментарий не сохранил.", reply_markup=after_save_keyboard(payload["operation_type"]))
        states_repo.set_state(user_id, ADDING_EXPENSE_AMOUNT, payload)
        return

    if state == ADDING_EXPENSE_ACTOR:
        await _handle_actor_change(update, user, text, payload)


async def _handle_category(update: Update, user_id: int, text: str, payload: dict):
    operation_type = payload["operation_type"]
    categories = EXPENSE_CATEGORIES if operation_type == "expense" else INCOME_CATEGORIES
    if text not in categories:
        await update.message.reply_text("Выберите категорию кнопкой 👇", reply_markup=categories_keyboard(operation_type))
        return

    payload["category"] = text
    if text == "📦 Прочее":
        states_repo.set_state(user_id, ADDING_EXPENSE_SUBCATEGORY, payload)
        await update.message.reply_text("Выберите подкатегорию:", reply_markup=other_subcategories_keyboard(operation_type))
        return

    payload["subcategory"] = None
    states_repo.set_state(user_id, ADDING_EXPENSE_AMOUNT, payload)
    await update.message.reply_text("Введите сумму:")


async def _handle_subcategory(update: Update, user_id: int, text: str, payload: dict):
    operation_type = payload["operation_type"]
    options = EXPENSE_OTHER_SUBCATEGORIES if operation_type == "expense" else INCOME_OTHER_SUBCATEGORIES
    if text not in options:
        await update.message.reply_text("Выберите подкатегорию кнопкой 👇", reply_markup=other_subcategories_keyboard(operation_type))
        return

    payload["subcategory"] = text
    states_repo.set_state(user_id, ADDING_EXPENSE_AMOUNT, payload)
    await update.message.reply_text("Введите сумму:")


async def _handle_amount(update: Update, user, text: str, payload: dict):
    try:
        amount = float(text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите сумму числом, например 1250 или 850.50")
        return

    operation_type = payload["operation_type"]
    operation_id = expense_service.add_operation(
        family_id=user["family_id"],
        created_by=user["telegram_id"],
        actor_id=user["telegram_id"],
        operation_type=operation_type,
        amount=amount,
        category=payload["category"],
        subcategory=payload.get("subcategory"),
        comment=None,
    )

    payload["last_operation_id"] = operation_id
    payload["amount"] = amount
    states_repo.set_state(user["telegram_id"], ADDING_EXPENSE_AMOUNT, payload)

    await update.message.reply_text(
        f"Сохранено ✅ {amount:.2f} ₽\nКатегория: {payload['category']}\nПо умолчанию записал на вас.",
        reply_markup=after_save_keyboard(operation_type),
    )
    activity_service.log(
        user["family_id"],
        user["telegram_id"],
        f"{operation_type}_add",
        f"добавил(а) {operation_type}: {amount:.2f} ₽ ({payload['category']})",
    )


async def _ask_actor(update: Update, user_id: int, family_id: int, payload: dict):
    members = users_repo.list_family_members(family_id)
    if len(members) <= 1:
        await update.message.reply_text("В семье только один участник — менять некого.", reply_markup=after_save_keyboard(payload["operation_type"]))
        return

    payload["member_map"] = {preferred_display_name(member): member["telegram_id"] for member in members}
    states_repo.set_state(user_id, ADDING_EXPENSE_ACTOR, payload)
    await update.message.reply_text(
        "Выберите участника:",
        reply_markup=who_keyboard(list(payload["member_map"].keys())),
    )


async def _handle_actor_change(update: Update, user, text: str, payload: dict):
    member_map = payload.get("member_map", {})
    if text == "👨‍👩‍👧 Общее":
        actor_id = None
    else:
        actor_id = member_map.get(text)
        if actor_id is None:
            await update.message.reply_text("Выберите участника кнопкой 👇", reply_markup=who_keyboard(list(member_map.keys())))
            return

    expense_service.update_actor(payload["last_operation_id"], user["family_id"], actor_id)
    states_repo.set_state(user["telegram_id"], ADDING_EXPENSE_AMOUNT, payload)
    await update.message.reply_text("Обновил участника операции ✅", reply_markup=after_save_keyboard(payload["operation_type"]))


async def _handle_back(update: Update, user_id: int, state: str | None, payload: dict):
    if state in {ADDING_EXPENSE_AMOUNT, ADDING_EXPENSE_SUBCATEGORY}:
        states_repo.set_state(user_id, ADDING_EXPENSE_CATEGORY, {"operation_type": payload.get("operation_type", "expense")})
        await update.message.reply_text(
            "Вернулись к выбору категории:",
            reply_markup=categories_keyboard(payload.get("operation_type", "expense")),
        )
    elif state in {ADDING_EXPENSE_COMMENT, ADDING_EXPENSE_ACTOR}:
        states_repo.set_state(user_id, ADDING_EXPENSE_AMOUNT, payload)
        await update.message.reply_text("Вернулись к быстрым действиям.", reply_markup=after_save_keyboard(payload.get("operation_type", "expense")))
    else:
        states_repo.clear_state(user_id)
        await update.message.reply_text("Финансы 💳", reply_markup=expenses_menu_keyboard())
