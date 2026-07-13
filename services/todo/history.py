import copy
import time


def push_history(data: dict, action: str) -> None:
    snapshot = {
        "branches": copy.deepcopy(data.get("branches", {})),
        "action": action,
        "time": int(time.time()),
    }

    history = data.setdefault("history", [])
    history.append(snapshot)

    if len(history) > 10:
        history.pop(0)
