from copy import deepcopy
from pathlib import Path
from config import config
from storage.json_storage import load_data, save_data

TODO_PATH = Path(config.data_dir) / "todo"
TODO_PATH.mkdir(parents=True, exist_ok=True)

DEFAULT_DATA = {
    "branches": {},
    "history": []
}

def load_todo(user_id: int):
    data = load_data(TODO_PATH, user_id)

    if not data:
        return deepcopy(DEFAULT_DATA)

    data.setdefault("branches", {})
    data.setdefault("history", [])

    return data

def save_todo(user_id: int, data):
    save_data(TODO_PATH, user_id, data)