import logging

from repos.family_repo import FamilyRepo
from repos.shopping_repo import ShoppingRepo
from repos.users_repo import UsersRepo

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

    def create_family(self, telegram_id: int, family_name: str):
        family = self.family_repo.create_family(family_name)
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
        return user, family, self.users_repo.list_family_members(user["family_id"])

    def regenerate_invite(self, telegram_id: int):
        user = self.users_repo.get_user(telegram_id)
        if not user or not user["family_id"] or not user["is_admin"]:
            return None
        return self.family_repo.regenerate_invite_code(user["family_id"])

    def update_role(self, telegram_id: int, role_key: str, role_label: str) -> None:
        self.users_repo.update_role(telegram_id, role_key, role_label)

    def role_label(self, member) -> str:
        return member["role_label"] or "Участник"

    def member_line(self, member) -> str:
        crown = "👑 " if member["is_admin"] else ""
        return f"{crown}{member['full_name']} — {self.role_label(member)}"

    def is_admin(self, telegram_id: int) -> bool:
        user = self.users_repo.get_user(telegram_id)
        return bool(user and user["is_admin"] and user["family_id"])
