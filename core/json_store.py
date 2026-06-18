import json
from pathlib import Path

def get_user_file(data_path: str | Path, user_id: int) -> Path:
    data_path = Path(data_path)
    data_path.mkdir(parents=True, exist_ok=True)

    return data_path / f"{user_id}.json"

def load_data(data_path: str | Path, user_id: int) -> list:
    file = get_user_file(data_path, user_id)

    if not file.exists():
        with open(file, "w", encoding="utf-8") as f:
            json.dump([], f)

        return []

    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data_path: str | Path, user_id: int, data: list) -> None:
    file = get_user_file(data_path, user_id)

    with open(file, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )