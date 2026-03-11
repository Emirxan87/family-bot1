def preferred_display_name(member) -> str:
    role_label = (member["role_label"] if "role_label" in member.keys() else None) if member else None
    if role_label and str(role_label).strip():
        return str(role_label).strip()

    full_name = (member["full_name"] if "full_name" in member.keys() else None) if member else None
    if full_name and str(full_name).strip():
        return str(full_name).strip()

    name = (member["name"] if "name" in member.keys() else None) if member else None
    if name and str(name).strip():
        return str(name).strip()

    return "Участник"
