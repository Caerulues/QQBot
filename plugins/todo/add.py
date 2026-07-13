import uuid
import re

from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.typing import T_State

from services.todo.history import push_history
from storage.todo_storage import load_todo, save_todo
from services.todo.search import find_tasks
from utils.parser import split_by_bar
from utils.command import get_cmd_start
from utils.choice_prompt import (
    ask_choice,
    parse_choice,
    format_todo_candidate,
)

cmd_start = get_cmd_start()


async def handle_add(
    cmd,
    args: list[str],
    raw_msg: str,
    data: dict,
    user_id: int,
    state: T_State
):
    if len(args) < 3:
        await cmd.finish(f"格式: {cmd_start}todo add -* <args1> | <args2>")

    sub = args[2]
    branches = data.setdefault("branches", {})

    # add -t <任务类名称> | <任务名称>
    if sub == "-t" or sub == "--task":
        content = re.sub(
            rf"^{re.escape(cmd_start)}todo\s+add\s+(?:=-t|--task)\s*",
            "",
            raw_msg,
            count=1
        ).strip()
        branch_name, task_name = split_by_bar(content)

        if not branch_name or not task_name:
            await cmd.finish(f"格式: {cmd_start}todo add -t <任务类名称> | <任务名称>")

        if branch_name not in branches:
            await cmd.finish(
                f"任务类不存在，请先使用 {cmd_start}todo branch <任务类名称> 创建"
            )

        task = {
            "id": str(uuid.uuid4())[:8],
            "name": task_name,
            "note": "",
            "done": False,
            "repeat": None
        }

        push_history(
            data,
            action=f"创建任务: {task_name}"
        )
        branches[branch_name].append(task)
        save_todo(user_id, data)
        await cmd.finish(f"已添加任务: {task_name}")

    # add -n <任务名称> | <任务备注>
    elif sub == "-n" or sub == "--note":
        content = re.sub(
            rf"^{re.escape(cmd_start)}todo\s+add\s+(?:=-n|--note)\s*",
            "",
            raw_msg,
            count=1
        ).strip()
        task_name, note = split_by_bar(content)

        if not task_name or not note:
            await cmd.finish(f"格式: {cmd_start}todo add -n <任务名称> | <任务备注>")

        matches = find_tasks(data, task_name)

        if not matches:
            await cmd.finish("未找到相关任务")

        if len(matches) == 1:
            await apply_add_note(
                cmd,
                data,
                user_id,
                matches[0],
                note
            )
            return

        await ask_choice(
            cmd,
            state,
            action="todo_add_note",
            candidates=matches,
            user_id=user_id,
            payload={"note": note},
            title="找到多个匹配项，请回复编号选择任务",
            formatter=lambda i, item: format_todo_candidate(
                i,
                item,
                note_label="原备注"
            ),
        )

    else:
        await cmd.finish("未知 add 参数")


async def apply_add_note(
    cmd,
    data: dict,
    user_id: int,
    target_item: dict,
    note: str
):
    branch_name = target_item["branch"]
    target = target_item["task"]
    target_id = target.get("id")

    if not target_id:
        await cmd.finish("任务缺少 id，可能是旧数据，请重新创建该任务")

    branches = data.get("branches", {})

    if branch_name not in branches:
        await cmd.finish("任务类不存在，可能已被修改或删除")

    tasks = branches[branch_name]

    for task in tasks:
        if task.get("id") != target_id:
            continue

        push_history(
            data,
            action=f"添加备注: {task['name']}"
        )

        task["note"] = note
        save_todo(user_id, data)
        await cmd.finish(f"已添加备注: {task['name']}")

    await cmd.finish("任务不存在，可能已被修改或删除")


async def receive_add_choice(cmd, event: MessageEvent, state: T_State):
    if state.get("pending_action") != "todo_add_note":
        return False

    choice = str(event.get_message()).strip()

    if not choice.isdigit():
        await cmd.reject("请输入数字编号")

    matches = state["candidates"]
    user_id = state["user_id"]
    note = state["payload"]["note"]

    index, target_item = await parse_choice(cmd, event, state)

    data = load_todo(user_id)

    await apply_add_note(
        cmd,
        data,
        user_id,
        target_item,
        note
    )

    return True