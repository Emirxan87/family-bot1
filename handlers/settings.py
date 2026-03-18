from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from keyboards.main_menu import main_menu_keyboard
from repos.location_repo import LocationRepo
from repos.states_repo import StatesRepo
from repos.users_repo import UsersRepo
from services.activity_service import ActivityService
from services.notification_service import NotificationService
from states import AWAITING_MEMORY_LOCATION
from utils.display_name import preferred_display_name

users_repo = UsersRepo()
location_repo = LocationRepo()
states_repo = StatesRepo()
activity_service = ActivityService()
notify_service = NotificationService()


def settings_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📍 Поделиться геопозицией", request_location=True)],
            [KeyboardButton("🧾 Активность семьи"), KeyboardButton("📍 Последние геопозиции")],
            [KeyboardButton("🏠 Главное меню")],
        ],
        resize_keyboard=True,
    )


async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ещё ⚙️", reply_markup=settings_menu_keyboard())


async def settings_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    user = users_repo.get_user(user_id)
    if not user or not user["family_id"]:
        await update.message.reply_text("Сначала присоединитесь к семье.", reply_markup=main_menu_keyboard())
        return

    if text == "🧾 Активность семьи":
        await update.message.reply_text(activity_service.latest_text(user["family_id"]))
    elif text == "📍 Последние геопозиции":
        rows = location_repo.latest_family(user["family_id"])
        if not rows:
            await update.message.reply_text("Пока никто не делился геопозицией.")
            return
        lines = ["📍 Последние геопозиции:"]
        for r in rows:
            lines.append(f"• {r['actor_name']}: {r['latitude']:.5f}, {r['longitude']:.5f}")
        await update.message.reply_text("\n".join(lines))
    elif text == "🏠 Главное меню":
        await update.message.reply_text("Главное меню", reply_markup=main_menu_keyboard())


async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state, _ = states_repo.get_state(user_id)
    if state == AWAITING_MEMORY_LOCATION:
        return
    user = users_repo.get_user(user_id)
    if not user or not user["family_id"]:
        return
    lat = update.message.location.latitude
    lon = update.message.location.longitude
    location_repo.save(user["family_id"], user_id, lat, lon)
    activity_service.log(user["family_id"], user_id, "location", "поделился(ась) геопозицией")
    await notify_service.notify_family(
        context.bot,
        user["family_id"],
        user_id,
        f"📍 {preferred_display_name(user)} поделился(ась) геопозицией: {lat:.5f}, {lon:.5f}",
    )
    await update.message.reply_text("Спасибо! Геопозиция сохранена.")
