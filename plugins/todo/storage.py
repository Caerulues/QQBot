from pathlib import Path
from core.config import config
from core.json_store import load_data, save_data

TODO_PATH = Path(config.data_dir) / "todo"
TODO_PATH.mkdir(parents=True, exist_ok=True)

DEFAULT_DATA = {
    "branches": {},
    "history": []
}

def load_todo(user_id: int):
    data = load_data(TODO_PATH, user_id)

    if not data:
        return DEFAULT_DATA.copy()

    data.setdefault("branches", {})
    data.setdefault("history", [])

    return data

def save_todo(user_id: int, data):
    save_data(TODO_PATH, user_id, data)