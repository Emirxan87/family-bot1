import logging

from repos.family_repo import FamilyRepo
from repos.shopping_repo import ShoppingRepo
from repos.users_repo import UsersRepo
from utils.display_name import preferred_display_name

logger = logging.getLogger(__name__)

ROLE_PRESETS = {
    "👨 Папа": ("father", "Папа"),
    "👩 Мама": ("mother", "Мама"),
    "👧 Дочка": ("daughter", "Дочка"),
    "👦 Сын": ("son", "Сын"),
    "👵 Бабушка": ("grandmother", "Бабушка"),
    "👴 Дедушка": ("grandfather", "Дедушка"),
}


class FamilyService:
    def __init__(self):
        self.family_repo = FamilyRepo()
        self.users_repo = UsersRepo()
        self.shopping_repo = ShoppingRepo()

    def ensure_user(self, tg_user) -> None:
        name = tg_user.full_name or tg_user.first_name or "Участник семьи"
        self.users_repo.upsert_user(tg_user.id, name, tg_user.username)

    def deep_link(self, bot_username: str | None, invite_code: str) -> str:
        if not bot_username:
            return f"/start join_{invite_code}"
        return f"https://t.me/{bot_username}?start=join_{invite_code}"

    def ensure_family_invite_code(self, family):
        if not family:
            return None
        invite_code = family["invite_code"] if "invite_code" in family.keys() else None
        if invite_code and str(invite_code).strip():
            return family
        family_id = family["id"] if "id" in family.keys() else None
        if not family_id:
            logger.error("Cannot restore invite_code: family has no id. keys=%s", list(family.keys()))
            return family
        logger.warning("Family %s has no invite_code. Regenerating.", family_id)
        restored = self.family_repo.regenerate_invite_code(family_id)
        if not restored:
            logger.error("Failed to restore invite_code for family_id=%s", family_id)
            return family
        return restored

    def create_family(self, telegram_id: int, family_name: str):
        family = self.family_repo.create_family(family_name)
        family = self.ensure_family_invite_code(family)
        self.users_repo.set_family(telegram_id, family["id"])
        self.users_repo.set_admin(telegram_id, True)
        user = self.users_repo.get_user(telegram_id)
        fallback_name = (user["full_name"] if user else "Родитель")
        self.users_repo.update_role(telegram_id, "custom", fallback_name)
        self.shopping_repo.ensure_default_lists(family["id"], telegram_id)
        return family

    def join_family(self, telegram_id: int, invite_code: str):
        family = self.family_repo.get_by_code(invite_code)
        if not family:
            return None
        family = self.ensure_family_invite_code(family)
        self.users_repo.set_family(telegram_id, family["id"])
        self.users_repo.set_admin(telegram_id, False)
        user = self.users_repo.get_user(telegram_id)
        if user and not user["role_label"]:
            self.users_repo.update_role(telegram_id, "custom", user["full_name"])
        self.shopping_repo.ensure_default_lists(family["id"], telegram_id)
        return family

    def user_family(self, telegram_id: int):
        user = self.users_repo.get_user(telegram_id)
        if not user or not user["family_id"]:
            return None, None, []
        family = self.family_repo.get_by_id(user["family_id"])
        if not family:
            return user, None, []
        family = self.ensure_family_invite_code(family)
        return user, family, self.users_repo.list_family_members(user["family_id"])

    def regenerate_invite(self, telegram_id: int):
        user = self.users_repo.get_user(telegram_id)
        if not user or not user["family_id"] or not user["is_admin"]:
            return None
        family = self.family_repo.regenerate_invite_code(user["family_id"])
        return self.ensure_family_invite_code(family)

    def update_role(self, telegram_id: int, role_key: str, role_label: str) -> None:
        self.users_repo.update_role(telegram_id, role_key, role_label)

    def role_label(self, member) -> str:
        role = member["role_label"] if "role_label" in member.keys() else None
        if role and str(role).strip():
            return str(role).strip()
        return "Участник"

    def member_display_name(self, member) -> str:
        return preferred_display_name(member)

    def member_line(self, member) -> str:
        crown = "👑 " if member["is_admin"] else ""
        return f"{crown}{self.member_display_name(member)}"

    def is_admin(self, telegram_id: int) -> bool:
        user = self.users_repo.get_user(telegram_id)
        return bool(user and user["is_admin"] and user["family_id"])
