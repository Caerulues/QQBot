import time
from .storage import save_todo


def push_history(data: dict, action: str):
    import copy

    snapshot = {
        "branches": copy.deepcopy(data.get("branches", {})),
        "action": action,
        "time": int(time.time())
    }

    history = data.setdefault("history", [])
    history.append(snapshot)

    if len(history) > 10:
        history.pop(0)


async def handle_revert(cmd, data: dict, user_id: int):
    history = data.setdefault("history", [])

    if not history:
        await cmd.finish("没有可撤销的操作")

    last = history.pop()

    data["branches"] = last["branches"]

    save_todo(user_id, data)

    action = last.get("action", "未知操作")

    await cmd.finish(
        f"已撤销：{action}"
    )