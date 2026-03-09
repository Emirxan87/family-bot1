def non_empty(value: str | None) -> bool:
    return bool((value or '').strip())
