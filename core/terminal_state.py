import json
from pathlib import Path
from typing import Optional


from core.config import config

TERMINAL_STATE_PATH = Path(config.data_dir) / "server_terminal.json"
TERMINAL_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)


def save_minecraft_window_id(window_id: int):
    with open(TERMINAL_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {"window_id": window_id},
            f,
            ensure_ascii=False,
            indent=2
        )


def load_minecraft_window_id() -> Optional[int]:
    if not TERMINAL_STATE_PATH.exists():
        return None

    try:
        with open(TERMINAL_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        window_id = data.get("window_id")

        if window_id is None:
            return None

        return int(window_id)

    except Exception:
        return None


def clear_minecraft_window_id():
    if TERMINAL_STATE_PATH.exists():
        TERMINAL_STATE_PATH.unlink()