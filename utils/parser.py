def maybe_number(value: str) -> float | None:
    try:
        return float(value.replace(',', '.'))
    except Exception:
        return None
