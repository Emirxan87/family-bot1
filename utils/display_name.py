ROLE_KEY_LABELS = {
    "father": "Папа",
    "mother": "Мама",
    "son": "Сын",
    "daughter": "Дочь",
}


def preferred_display_name(member) -> str:
    if not member:
        return "Участник"

    role_label = member["role_label"] if "role_label" in member.keys() else None
    if role_label and str(role_label).strip():
        return str(role_label).strip()

    role_key = member["role_key"] if "role_key" in member.keys() else None
    if role_key in ROLE_KEY_LABELS:
        return ROLE_KEY_LABELS[role_key]

    return "Участник"
