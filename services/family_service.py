from repos.family_repo import FamilyRepo
from repos.shopping_repo import ShoppingRepo
from repos.users_repo import UsersRepo


class FamilyService:
    def __init__(self):
        self.family_repo = FamilyRepo()
        self.users_repo = UsersRepo()
        self.shopping_repo = ShoppingRepo()

    def ensure_user(self, tg_user) -> None:
        name = tg_user.full_name or tg_user.first_name or "Участник семьи"
        self.users_repo.upsert_user(tg_user.id, name, tg_user.username)

    def create_family(self, telegram_id: int, family_name: str):
        family = self.family_repo.create_family(family_name)
        self.users_repo.set_family(telegram_id, family["id"])
        self.shopping_repo.ensure_default_lists(family["id"], telegram_id)
        return family

    def join_family(self, telegram_id: int, invite_code: str):
        family = self.family_repo.get_by_code(invite_code)
        if not family:
            return None
        self.users_repo.set_family(telegram_id, family["id"])
        self.shopping_repo.ensure_default_lists(family["id"], telegram_id)
        return family

    def family_info_text(self, telegram_id: int) -> str:
        user = self.users_repo.get_user(telegram_id)
        if not user or not user["family_id"]:
            return "Вы пока не состоите в семье."
        family = self.family_repo.get_by_id(user["family_id"])
        members = self.users_repo.list_family_members(user["family_id"])
        lines = [
            f"👨‍👩‍👧‍👦 Семья: {family['name']}",
            f"Invite code: `{family['invite_code']}`",
            "",
            "Участники:",
        ]
        lines.extend([f"• {m['full_name']}" for m in members])
        return "\n".join(lines)
