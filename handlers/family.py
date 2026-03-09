from telegram import Update
from telegram.ext import ContextTypes

from keyboards.family import family_menu_keyboard
from keyboards.main_menu import main_menu_keyboard
from repos.users_repo import UsersRepo
from repos.states_repo import StatesRepo
from services.activity_service import ActivityService
from services.family_service import FamilyService
from states import INVITING_FAMILY_MEMBER

family_service = FamilyService()
activity_service = ActivityService()
users_repo = UsersRepo()
states_repo = StatesRepo()


async def family_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Раздел семьи 👨‍👩‍👧‍👦", reply_markup=family_menu_keyboard())


async def family_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id

    state, _ = states_repo.get_state(user_id)
    if state == INVITING_FAMILY_MEMBER:
        family = family_service.join_family(user_id, text)
        states_repo.clear_state(user_id)
        if not family:
            await update.message.reply_text("Код не найден. Проверьте invite code и попробуйте снова.")
            return
        activity_service.log(family["id"], user_id, "family_join", "присоединился к семье")
        await update.message.reply_text(
            f"Добро пожаловать в семью «{family['name']}» 🤍", reply_markup=main_menu_keyboard()
        )
        return

    if text == "➕ Создать семью":
        created = family_service.create_family(user_id, "Наша семья")
        activity_service.log(created["id"], user_id, "family_create", "создал(а) семью")
        await update.message.reply_text(
            f"Семья создана!\nInvite code: `{created['invite_code']}`",
            parse_mode="Markdown",
            reply_markup=family_menu_keyboard(),
        )
    elif text == "🔑 Вступить по коду":
        states_repo.set_state(user_id, INVITING_FAMILY_MEMBER)
        await update.message.reply_text("Введите invite code семьи (например, ABC123):")
    elif text == "👥 Участники":
        text_info = family_service.family_info_text(user_id)
        await update.message.reply_text(text_info, parse_mode="Markdown", reply_markup=family_menu_keyboard())
    elif text == "🏠 Главное меню":
        await update.message.reply_text("Возвращаемся в главное меню", reply_markup=main_menu_keyboard())
