from datetime import datetime


def is_date(value: str) -> bool:
    try:
        datetime.strptime(value, '%Y-%m-%d')
        return True
    except ValueError:
        return False
