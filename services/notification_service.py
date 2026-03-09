import logging

from repos.users_repo import UsersRepo


class NotificationService:
    def __init__(self):
        self.users_repo = UsersRepo()

    async def notify_family(self, bot, family_id: int, actor_id: int, text: str):
        members = self.users_repo.list_family_members(family_id)
        for member in members:
            if member["telegram_id"] == actor_id:
                continue
            try:
                await bot.send_message(chat_id=member["telegram_id"], text=text)
            except Exception as exc:
                logging.warning("Failed to notify %s: %s", member["telegram_id"], exc)
