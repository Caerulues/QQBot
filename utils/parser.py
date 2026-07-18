def split_by_bar(text: str):
    if "|" not in text:
        return None, None

    left, right = text.split("|")
    return left.strip(), right.strip()