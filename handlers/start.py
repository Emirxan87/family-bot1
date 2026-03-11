import logging

from telegram import Update
from telegram.ext import ContextTypes

from keyboards.family import family_role_keyboard
from keyboards.main_menu import main_menu_keyboard
from messages import MAIN_HELP, WELCOME
from repos.states_repo import StatesRepo
from services.activity_service import ActivityService
from services.family_service import FamilyService
from states import AWAITING_FAMILY_ROLE

logger = logging.getLogger(__name__)
family_service = FamilyService()
states_repo = StatesRepo()
activity_service = ActivityService()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    family_service.ensure_user(update.effective_user)

    try:
        args = context.args or []
        if args and args[0].startswith("join_"):
            invite_code = args[0][5:]
            family = family_service.join_family(update.effective_user.id, invite_code)
            if family:
                activity_service.log(family["id"], update.effective_user.id, "family_join", "присоединился по ссылке")
                states_repo.set_state(update.effective_user.id, AWAITING_FAMILY_ROLE)
                await update.message.reply_text(
                    f"Вы в семье «{family['name']}» ✅\nКак вас подписать в семье?",
                    reply_markup=family_role_keyboard(),
                )
                return
            await update.message.reply_text("Ссылка устарела или неверная")
    except Exception:
        logger.exception("Failed to process deep link start")

    await update.message.reply_text(WELCOME, reply_markup=main_menu_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MAIN_HELP, reply_markup=main_menu_keyboard())


async def to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Главное меню", reply_markup=main_menu_keyboard())
