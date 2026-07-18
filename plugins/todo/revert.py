from storage.todo_storage import save_todo


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