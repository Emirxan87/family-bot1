from telegram import Update
from telegram.ext import ContextTypes

from keyboards.main_menu import main_menu_keyboard
from keyboards.memories import location_request_keyboard, memories_menu_keyboard
from repos.states_repo import StatesRepo
from repos.users_repo import UsersRepo
from services.activity_service import ActivityService
from services.memory_service import MemoryService
from services.notification_service import NotificationService
from states import AWAITING_MEMORY_CAPTION, AWAITING_MEMORY_LOCATION, AWAITING_MEMORY_PHOTO

users_repo = UsersRepo()
states_repo = StatesRepo()
memory_service = MemoryService()
activity_service = ActivityService()
notify_service = NotificationService()


async def memories_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Моменты 📸", reply_markup=memories_menu_keyboard())


async def memories_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    user = users_repo.get_user(user_id)
    if not user or not user["family_id"]:
        await update.message.reply_text("Сначала присоединитесь к семье.", reply_markup=main_menu_keyboard())
        return

    state, payload = states_repo.get_state(user_id)
    if text == "➕ Добавить момент":
        states_repo.set_state(user_id, AWAITING_MEMORY_PHOTO, {})
        await update.message.reply_text("Пришлите фотографию момента ✨")
    elif text == "🖼 Лента моментов":
        moments = memory_service.feed(user["family_id"])
        if not moments:
            await update.message.reply_text("Пока в ленте пусто.")
            return
        for moment in moments:
            caption = _build_caption(moment)
            await update.message.reply_photo(moment["photo_file_id"], caption=caption)
    elif text == "🏠 Главное меню":
        await update.message.reply_text("Главное меню", reply_markup=main_menu_keyboard())
    elif state == AWAITING_MEMORY_CAPTION:
        payload["caption"] = text if text != "⏭ Пропустить" else ""
        states_repo.set_state(user_id, AWAITING_MEMORY_LOCATION, payload)
        await update.message.reply_text(
            "Хотите добавить геопозицию к моменту?", reply_markup=location_request_keyboard()
        )


async def memory_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state, payload = states_repo.get_state(user_id)
    if state != AWAITING_MEMORY_PHOTO:
        return
    photo = update.message.photo[-1]
    payload["photo_file_id"] = photo.file_id
    states_repo.set_state(user_id, AWAITING_MEMORY_CAPTION, payload)
    await update.message.reply_text("Добавьте подпись к фото или нажмите «⏭ Пропустить».")


async def memory_location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = users_repo.get_user(user_id)
    state, payload = states_repo.get_state(user_id)
    if state != AWAITING_MEMORY_LOCATION:
        return

    lat = lon = None
    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude

    result = memory_service.save_moment(
        family_id=user["family_id"],
        user_id=user_id,
        photo_file_id=payload.get("photo_file_id"),
        caption=payload.get("caption", ""),
        latitude=lat,
        longitude=lon,
    )
    states_repo.clear_state(user_id)
    activity_service.log(user["family_id"], user_id, "moment_add", "добавил(а) семейный момент")
    await notify_service.notify_family(
        context.bot,
        user["family_id"],
        user_id,
        f"📸 {user['full_name']} поделился(ась) новым моментом",
    )
    await update.message.reply_text("Сохранил момент в семейной ленте 💛", reply_markup=memories_menu_keyboard())
    await update.message.reply_photo(payload.get("photo_file_id"), caption=_build_saved_caption(result))


def _build_caption(moment):
    text = moment["caption"] or ""
    meta = []
    if moment["city"]:
        meta.append(moment["city"])
    if moment["weather"]:
        t = f", {moment['temperature']}°C" if moment["temperature"] is not None else ""
        meta.append(f"{moment['weather']}{t}")
    if meta:
        text += "\n" + " • ".join(meta)
    return text or "Семейный момент"


def _build_saved_caption(result: dict):
    text = result.get("caption") or "Семейный момент"
    extra = []
    if result.get("city"):
        extra.append(result["city"])
    if result.get("place"):
        extra.append(result["place"])
    if result.get("weather"):
        temp = result.get("temperature")
        extra.append(f"{result['weather']} {temp}°C" if temp is not None else result["weather"])
    if extra:
        text += "\n" + "\n".join([f"• {x}" for x in extra])
    return text
