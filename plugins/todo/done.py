from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
from nonebot.typing import T_State

from .storage import load_todo, save_todo
from .search import find_tasks
from .revert import push_history
from core.command import get_cmd_start
from utils.render_image import render_image

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
        push_history(
            data,
            action=f"完成任务：{task['name']}"
        )
        target = matches[0]["task"]
        target["done"] = True

        save_todo(user_id, data)
        await cmd.finish(f"已完成：{target['name']}")

    state["pending_action"] = "todo_done"
    state["candidates"] = matches
    state["user_id"] = user_id

    lines = [
        "找到多个匹配项，请回复编号选择要完成哪一项",
        ""
    ]

    for i, item in enumerate(matches):
        task = item["task"]
        note = task.get("note", "")

        status = "已完成" if task.get("done") else "未完成"

        if note:
            right = f"{status} | 备注：{note}"
        else:
            right = status

        lines.append(
            f"{i + 1}. {item['branch']}: {task['name']} - {right}"
        )

    image_bytes = render_image(lines)
    await cmd.send(MessageSegment.image(image_bytes))
    await cmd.pause()

async def receive_done_choice(cmd, event: MessageEvent, state: T_State):
    if state.get("pending_action") != "todo_done":
        return False

    choice = str(event.get_message()).strip()

    if not choice.isdigit():
        await cmd.reject("编号不存在，请重新输入数字编号")

    matches = state["candidates"]
    user_id = state["user_id"]

    index = int(choice) - 1

    if index < 0 or index >= len(matches):
        await cmd.reject("编号不存在，请重新输入")

    target = matches[index]["task"]
    target_id = target["id"]

    data = load_todo(user_id)

    for tasks in data.get("branches", {}).values():
        for task in tasks:
            if len(matches) == 1:
                target = matches[0]["task"]

                push_history(
                    data,
                    action=f"完成任务：{target['name']}"
                )

                target["done"] = True
                save_todo(user_id, data)

                await cmd.finish(f"已完成：{target['name']}")

    await cmd.finish("任务不存在，可能已被修改或删除")