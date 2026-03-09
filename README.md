# Family Bot (Telegram + SQLite)

Все файлы новой модульной структуры уже загружены в проект `family-bot1`.

## Структура проекта

```text
.
├── bot.py
├── config.py
├── database.py
├── messages.py
├── states.py
├── handlers/
├── keyboards/
├── repos/
├── services/
├── utils/
└── requirements.txt
```

## Быстрый запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
export DB_PATH="./family.db"
# optional:
export OPENWEATHER_API_KEY="YOUR_OPENWEATHER_KEY"

python bot.py
```

## Проверка, что БД инициализируется

```bash
DB_PATH=/tmp/family_test.db python - <<'PY'
from database import init_db, get_conn
init_db()
with get_conn() as conn:
    for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        print(row[0])
PY
```
