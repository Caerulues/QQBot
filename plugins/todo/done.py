from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.typing import T_State

from .storage import load_todo, save_todo
from .search import find_tasks
from .revert import push_history
from core.command import get_cmd_start
from utils.choice_prompt import (
    ask_choice,
    parse_choice,
    format_todo_candidate,
)

cmd_start = get_cmd_start()

async def handle_done(
    cmd,
    args: list[str],
    raw_msg: str,
    data: dict,
    user_id: int,
    state: T_State
):
    content = raw_msg.replace(f"{cmd_start}todo done", "", 1).strip()

    if not content:
        await cmd.finish(f"格式：{cmd_start}todo done <任务名称>")

    matches = find_tasks(data, content)

    if not matches:
        await cmd.finish("未找到相关任务")

    if len(matches) == 1:
        target = matches[0]["task"]

        push_history(
            data,
            action=f"完成任务：{target['name']}"
        )

        target["done"] = True
        save_todo(user_id, data)

        await cmd.finish(f"已完成：{target['name']}")

    await ask_choice(
        cmd,
        state,
        action="todo_done",
        candidates=matches,
        user_id=user_id,
        title="找到多个匹配项，请回复编号选择要完成哪一项",
        formatter=format_todo_candidate,
    )

async def receive_done_choice(cmd, event: MessageEvent, state: T_State):
    if state.get("pending_action") != "todo_done":
        return False

    choice = str(event.get_message()).strip()

    if not choice.isdigit():
        await cmd.reject("编号不存在，请重新输入数字编号")

    matches = state["candidates"]
    user_id = state["user_id"]

    index, target_item = await parse_choice(cmd, event, state)

    target = target_item["task"]
    target_id = target.get("id")

    if not target_id:
        await cmd.finish("任务缺少 id，可能是旧数据，请重新创建该任务")

    data = load_todo(user_id)

    for tasks in data.get("branches", {}).values():
        for task in tasks:
            if task.get("id") != target_id:
                continue

            push_history(
                data,
                action=f"完成任务：{task['name']}"
            )

            task["done"] = True
            save_todo(user_id, data)

            await cmd.finish(f"已完成：{task['name']}")

    await cmd.finish("任务不存在，可能已被修改或删除")