import logging

from telegram import Update
from telegram.ext import ContextTypes

from keyboards.family import (
    family_manage_keyboard,
    family_member_actions_keyboard,
    family_role_keyboard,
    family_start_keyboard,
)
from keyboards.main_menu import main_menu_keyboard
from repos.states_repo import StatesRepo
from services.activity_service import ActivityService
from services.family_service import FamilyService, ROLE_PRESETS
from states import AWAITING_FAMILY_CUSTOM_ROLE, AWAITING_FAMILY_ROLE, INVITING_FAMILY_MEMBER

logger = logging.getLogger(__name__)
family_service = FamilyService()
activity_service = ActivityService()
states_repo = StatesRepo()

MAX_CUSTOM_ROLE_LEN = 40


def _sanitize_custom_role(raw_text: str) -> str:
    return " ".join((raw_text or "").split())


def _is_onboarding_flow(payload: dict) -> bool:
    return payload.get("source") == "onboarding"


def _role_saved_text(role_label: str, onboarding: bool) -> str:
    clean_label = role_label.strip()
    if onboarding:
        return f"Готово ✅ Теперь вы в семье как: {clean_label}"
    return "Роль обновлена ✅"


def _can_manage_member_role(actor_id: int, target_id: int, is_admin: bool) -> bool:
    return actor_id == target_id or is_admin


def _target_role_saved_text(actor_id: int, target_member, role_label: str, onboarding: bool) -> str:
    if onboarding:
        return _role_saved_text(role_label, onboarding=True)
    if target_member and actor_id != target_member["telegram_id"]:
        display_name = family_service.member_display_name(target_member)
        return f"Готово ✅ Теперь {display_name}: {role_label.strip()}"
    return "Готово ✅ Роль изменена"


def _role_saved_keyboard(onboarding: bool):
    if onboarding:
        return main_menu_keyboard()
    return family_manage_keyboard()


def _invite_text(bot_username: str | None, family) -> str:
    safe_family = family_service.ensure_family_invite_code(family)
    if not safe_family or "invite_code" not in safe_family.keys() or not safe_family["invite_code"]:
        logger.error(
            "Unable to render invite link: missing invite_code. family_id=%s keys=%s",
            safe_family["id"] if safe_family and "id" in safe_family.keys() else None,
            list(safe_family.keys()) if safe_family else [],
        )
        return "Ссылка приглашения временно недоступна. Попробуйте обновить код позже."

    code = safe_family["invite_code"]
    link = family_service.deep_link(bot_username, code)
    return (
        "Отправьте эту ссылку члену семьи:\n"
        f"{link}\n\n"
        "Если ссылка не сработает, можно ввести код:\n"
        f"{code}"
    )


async def _show_no_family(update: Update):
    await update.message.reply_text("У вас пока нет семьи", reply_markup=family_start_keyboard())


async def _show_family(update: Update, bot_username: str | None, telegram_id: int):
    user, family, members = family_service.user_family(telegram_id)
    if not user or not family:
        await _show_no_family(update)
        return
    lines = ["👨‍👩‍👧 Ваша семья", "", "Участники:"]
    lines.extend([f"• {family_service.member_line(m)}" for m in members] or ["• Пока никого"])
    lines.extend(["", _invite_text(bot_username, family)])
    await update.message.reply_text("\n".join(lines), reply_markup=family_manage_keyboard())


async def family_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await _show_family(update, context.bot.username, update.effective_user.id)
    except Exception:
        logger.exception("Failed to open family menu")
        await update.message.reply_text("Не получилось открыть раздел Семья")


async def family_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id

    try:
        state, payload = states_repo.get_state(user_id)

        if text == "⬅️ Назад":
            states_repo.clear_state(user_id)
            await update.message.reply_text("Главное меню", reply_markup=main_menu_keyboard())
            return

        if state == INVITING_FAMILY_MEMBER:
            family = family_service.join_family(user_id, text)
            states_repo.clear_state(user_id)
            if not family:
                await update.message.reply_text("Код не найден. Попробуйте ещё раз.")
                return
            activity_service.log(family["id"], user_id, "family_join", "присоединился к семье")
            states_repo.set_state(
                user_id,
                AWAITING_FAMILY_ROLE,
                {"mode": "set_role", "target": user_id, "source": "onboarding"},
            )
            await update.message.reply_text("Как вас подписать в семье?", reply_markup=family_role_keyboard())
            return

        if state == AWAITING_FAMILY_ROLE and payload.get("mode") == "choose_member":
            requester, family, members = family_service.user_family(user_id)
            if not family:
                states_repo.clear_state(user_id)
                await _show_no_family(update)
                return
            is_admin = bool(requester and requester["is_admin"])
            if not text.isdigit() or not (1 <= int(text) <= len(members)):
                await update.message.reply_text("Введите номер участника")
                return
            member = members[int(text) - 1]
            if not _can_manage_member_role(user_id, member["telegram_id"], is_admin):
                states_repo.clear_state(user_id)
                await update.message.reply_text("Можно менять только свою роль. Чужие роли доступны администратору семьи.")
                return
            if member["telegram_id"] == user_id:
                states_repo.set_state(user_id, AWAITING_FAMILY_ROLE, {"mode": "set_role", "target": user_id})
                await update.message.reply_text("Выберите роль", reply_markup=family_role_keyboard())
                return
            states_repo.set_state(user_id, AWAITING_FAMILY_ROLE, {"mode": "member_actions", "target": member["telegram_id"]})
            await update.message.reply_text(
                "Выберите действие для участника",
                reply_markup=family_member_actions_keyboard(),
            )
            return

        if state == AWAITING_FAMILY_ROLE and payload.get("mode") == "member_actions":
            target = payload.get("target")
            if not family_service.can_manage_role(user_id, target):
                states_repo.clear_state(user_id)
                await update.message.reply_text("Можно управлять только своей ролью", reply_markup=family_manage_keyboard())
                return
            if text == "✏️ Изменить роль":
                states_repo.set_state(user_id, AWAITING_FAMILY_ROLE, {"mode": "set_role", "target": target})
                await update.message.reply_text("Выберите роль", reply_markup=family_role_keyboard())
                return
            if text == "👑 Назначить админом":
                family_service.users_repo.set_admin(target, True)
                states_repo.clear_state(user_id)
                await update.message.reply_text("Участник теперь админ ✅", reply_markup=family_manage_keyboard())
                return
            if text == "🗑 Удалить из семьи":
                family_service.users_repo.remove_from_family(target)
                states_repo.clear_state(user_id)
                await update.message.reply_text("Участник удален из семьи", reply_markup=family_manage_keyboard())
                return
            await update.message.reply_text("Нажмите кнопку ниже 👇", reply_markup=family_member_actions_keyboard())
            return

        if state == AWAITING_FAMILY_ROLE and payload.get("mode") == "set_role":
            target = payload.get("target", user_id)
            onboarding = _is_onboarding_flow(payload)
            if not family_service.can_manage_role(user_id, target):
                states_repo.clear_state(user_id)
                await update.message.reply_text("Можно менять только свою роль", reply_markup=family_manage_keyboard())
                return
            if text == "✏️ Свое название":
                states_repo.set_state(
                    user_id,
                    AWAITING_FAMILY_CUSTOM_ROLE,
                    {"target": target, "source": payload.get("source")},
                )
                await update.message.reply_text(
                    f"Напишите, как вас подписать в семье (до {MAX_CUSTOM_ROLE_LEN} символов)",
                )
                return
            role_data = ROLE_PRESETS.get(text)
            if role_data:
                family_service.update_role(target, role_data[0], role_data[1])
                target_member = family_service.users_repo.get_user(target)
                states_repo.clear_state(user_id)
                await update.message.reply_text(
                    _target_role_saved_text(user_id, target_member, role_data[1], onboarding),
                    reply_markup=_role_saved_keyboard(onboarding),
                )
                return

        if state == AWAITING_FAMILY_CUSTOM_ROLE:
            target = payload.get("target", user_id)
            onboarding = _is_onboarding_flow(payload)
            if not family_service.can_manage_role(user_id, target):
                states_repo.clear_state(user_id)
                await update.message.reply_text("Можно менять только свою роль", reply_markup=family_manage_keyboard())
                return
            role = _sanitize_custom_role(text)
            if not role:
                await update.message.reply_text("Название не должно быть пустым. Напишите роль словами.")
                return
            if len(role) > MAX_CUSTOM_ROLE_LEN:
                await update.message.reply_text(
                    f"Слишком длинно — максимум {MAX_CUSTOM_ROLE_LEN} символов. Попробуйте короче.",
                )
                return
            family_service.update_role(target, "custom", role)
            target_member = family_service.users_repo.get_user(target)
            states_repo.clear_state(user_id)
            await update.message.reply_text(
                _target_role_saved_text(user_id, target_member, role, onboarding),
                reply_markup=_role_saved_keyboard(onboarding),
            )
            return

        if text == "➕ Создать семью":
            created = family_service.create_family(user_id, "Наша семья")
            activity_service.log(created["id"], user_id, "family_create", "создал(а) семью")
            await _show_family(update, context.bot.username, user_id)
            return

        if text in {"🔗 Вступить по ссылке/коду", "🔑 Вступить по коду"}:
            states_repo.set_state(user_id, INVITING_FAMILY_MEMBER)
            await update.message.reply_text("Введите код приглашения")
            return

        if text == "➕ Пригласить":
            _, family, _ = family_service.user_family(user_id)
            if not family:
                await _show_no_family(update)
                return
            await update.message.reply_text(_invite_text(context.bot.username, family))
            return

        if text == "👥 Участники":
            _, family, members = family_service.user_family(user_id)
            if not family:
                await _show_no_family(update)
                return
            lines = ["Участники:"] + [f"{i}. {family_service.member_line(m)}" for i, m in enumerate(members, 1)]
            lines.append("\nВыберите номер участника")
            states_repo.set_state(user_id, AWAITING_FAMILY_ROLE, {"mode": "choose_member"})
            await update.message.reply_text("\n".join(lines), reply_markup=family_manage_keyboard())
            return

        if text == "✏️ Роли":
            requester, family, members = family_service.user_family(user_id)
            if not family:
                await _show_no_family(update)
                return
            is_admin = bool(requester and requester["is_admin"])
            if not is_admin:
                members = [member for member in members if member["telegram_id"] == user_id]
                lines = ["Вы можете изменить только свою роль:"]
            else:
                lines = ["Кому поменять роль?"]
            lines.extend([f"{i}. {family_service.member_line(m)}" for i, m in enumerate(members, 1)])
            states_repo.set_state(user_id, AWAITING_FAMILY_ROLE, {"mode": "choose_member"})
            await update.message.reply_text("\n".join(lines), reply_markup=family_manage_keyboard())
            return

        if text == "🔑 Новый код и ссылка":
            family = family_service.regenerate_invite(user_id)
            if not family:
                await update.message.reply_text("Только админ может обновить код")
                return
            await update.message.reply_text(_invite_text(context.bot.username, family))
            return

    except Exception:
        logger.exception("Family router failure: user_id=%s text=%s", user_id, text)
        await update.message.reply_text("Ошибка в разделе Семья. Попробуйте ещё раз.")
