from telegram import Update
from telegram.ext import ContextTypes

from keyboards.main_menu import main_menu_keyboard
from messages import MAIN_HELP, WELCOME
from services.family_service import FamilyService

family_service = FamilyService()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    family_service.ensure_user(update.effective_user)
    await update.message.reply_text(WELCOME, reply_markup=main_menu_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MAIN_HELP, reply_markup=main_menu_keyboard())


async def to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Главное меню", reply_markup=main_menu_keyboard())
