import json
from pathlib import Path
from typing import Optional

from core.config import config

TERMINAL_STATE_PATH = Path(config.data_dir) / "server_terminal.json"
TERMINAL_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_state() -> dict:
    if not TERMINAL_STATE_PATH.exists():
        return {}

    try:
        with open(TERMINAL_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(data: dict):
    with open(TERMINAL_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_minecraft_window_id(window_id: int):
    data = _load_state()
    data["window_id"] = int(window_id)
    _save_state(data)


def load_minecraft_window_id() -> Optional[int]:
    try:
        window_id = _load_state().get("window_id")
        return int(window_id) if window_id is not None else None
    except Exception:
        return None


def clear_minecraft_window_id():
    data = _load_state()
    data.pop("window_id", None)
    if data:
        _save_state(data)
    elif TERMINAL_STATE_PATH.exists():
        TERMINAL_STATE_PATH.unlink()


def save_minecraft_pid(pid: int):
    data = _load_state()
    data["pid"] = int(pid)
    _save_state(data)


def load_minecraft_pid() -> Optional[int]:
    try:
        pid = _load_state().get("pid")
        return int(pid) if pid is not None else None
    except Exception:
        return None


def clear_minecraft_pid():
    data = _load_state()
    data.pop("pid", None)
    if data:
        _save_state(data)
    elif TERMINAL_STATE_PATH.exists():
        TERMINAL_STATE_PATH.unlink()


def clear_minecraft_state():
    if TERMINAL_STATE_PATH.exists():
        TERMINAL_STATE_PATH.unlink()
