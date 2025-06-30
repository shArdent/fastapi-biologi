import re


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"[^\w-]", "", text)
    return text
