from pathlib import Path
from dotenv import dotenv_values
import ast

def get_cmd_start() -> str:
    raw = dotenv_values(Path(".env")).get("COMMAND_START")

    if raw is None:
        return ""

    value = ast.literal_eval(raw)

    if isinstance(value, list) and value:
        return str(value[0])

    return ""

def split_command(text: str) -> tuple[str, str]:
    text = text.strip()

    for start in get_cmd_start():
        if text.startswith(start):
            without_start = text[len(start):].strip()
            parts = without_start.split(maxsplit=1)

            command = parts[0] if parts else ""
            rest = parts[1] if len(parts) > 1 else ""

            return command, rest

    return "", text