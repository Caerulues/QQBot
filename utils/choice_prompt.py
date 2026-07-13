from datetime import datetime
from typing import Any, Callable

from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.typing import T_State

from utils.build_help_image import render_image


async def ask_choice(
    cmd,
    state: T_State,
    *,
    action: str,
    candidates: list,
    user_id: int,
    title: str,
    formatter: Callable[[int, Any], str],
    payload: dict | None = None,
):
    state["pending_action"] = action
    state["candidates"] = candidates
    state["user_id"] = user_id
    state["payload"] = payload or {}

    lines = [
        title,
        ""
    ]

    for i, item in enumerate(candidates):
        lines.append(formatter(i, item))

    image_bytes = render_image(lines)

    # 用 reject，不用 send + pause
    # 避免第一次编号输入只恢复 matcher，但没有被业务逻辑处理
    await cmd.reject(MessageSegment.image(image_bytes))


async def parse_choice(cmd, event, state: T_State):
    choice = str(event.get_message()).strip()

    if not choice.isdigit():
        await cmd.reject("请输入数字编号")

    matches = state["candidates"]
    index = int(choice) - 1

    if index < 0 or index >= len(matches):
        await cmd.reject("编号不存在，请重新输入")

    return index, matches[index]


def format_todo_candidate(i: int, item: dict, note_label: str = "备注") -> str:
    task = item["task"]
    note = task.get("note", "")
    status = "已完成" if task.get("done") else "未完成"

    if note:
        right = f"{status} | {note_label}：{note}"
    else:
        right = status

    return f"{i + 1}. {item['branch']} / {task['name']} - {right}"


def format_ddl_candidate(i: int, item: dict) -> str:
    time_text = datetime.fromtimestamp(item["time"]).strftime("%Y-%m-%d %H:%M")
    return f"{i + 1}. {item['title']} - {time_text}"