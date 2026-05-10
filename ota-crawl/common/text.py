import re


def clean_text(value: str | None) -> str | None:
    if not value:
        return None
    result = re.sub(r"\s+", " ", value).strip()
    return result or None

