import secrets
import string

from database import get_conn


class FamilyRepo:
    def _invite_code(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(6))

    def create_family(self, name: str) -> dict:
        with get_conn() as conn:
            code = self._invite_code()
            while conn.execute(
                "SELECT 1 FROM families WHERE invite_code = ?", (code,)
            ).fetchone():
                code = self._invite_code()
            cur = conn.execute(
                "INSERT INTO families(name, invite_code) VALUES(?, ?)", (name, code)
            )
            family_id = cur.lastrowid
            return {"id": family_id, "invite_code": code, "name": name}

    def get_by_code(self, code: str):
        with get_conn() as conn:
            return conn.execute(
                "SELECT * FROM families WHERE invite_code = ?", (code.upper(),)
            ).fetchone()

    def get_by_id(self, family_id: int):
        with get_conn() as conn:
            return conn.execute("SELECT * FROM families WHERE id = ?", (family_id,)).fetchone()
