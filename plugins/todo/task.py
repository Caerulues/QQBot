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
    format_todo_candidate
)

cmd_start = get_cmd_start()

async def handle_task(
    cmd,
    args: list[str],
    raw_msg: str,
    data: dict,
    user_id: int,
    state: T_State
):
    if len(args) < 3:
        await cmd.finish(f"格式: {cmd_start}todo task -* <args>")

    sub = args[2]

    if sub in ("-m", "--modify"):
        await handle_task_modify(cmd, raw_msg, data, user_id, state)

    elif sub in ("-d", "--delete"):
        await handle_task_delete(cmd, raw_msg, data, user_id, state)

    elif sub in ("-r", "--routine"):
        await handle_task_repeat(cmd, raw_msg, data, user_id, state)

    else:
        await cmd.finish("未知 task 参数")


async def handle_task_modify(cmd, raw_msg: str, data: dict, user_id: int, state: T_State):
    content = re.sub(
        rf"^{re.escape(cmd_start)}todo\s+task\s+(?:-m|--modify)\s*",
        "",
        raw_msg,
        count=1
    ).strip()

    # task -m <任务名称> -n <新备注>
    if re.search(r"\s(?:-n|--note)\s", content):
        task_name, new_note = re.split(
            r"\s+(?:-n|--note)\s+",
            content,
            maxsplit=1
        )

        task_name = task_name.strip()
        new_note = new_note.strip()

        if not task_name or not new_note:
            await cmd.finish(
                f"格式: {cmd_start}todo task -m <任务名称> -n <新任务备注>"
            )

        matches = find_tasks(data, task_name)

        if not matches:
            await cmd.finish("未找到相关任务")

        payload = {
            "new_note": new_note
        }

        await apply_or_wait(
            cmd,
            data,
            user_id,
            state,
            matches,
            "todo_task_modify_note",
            payload
        )
        return

    # task -m <原任务名称> | <新任务名称>
    old_name, new_name = split_by_bar(content)

    if not old_name or not new_name:
        await cmd.finish(f"格式: {cmd_start}todo task -m <原任务名称> | <新任务名称>")

    matches = find_tasks(data, old_name)

    if not matches:
        await cmd.finish("未找到相关任务")

    payload = {
        "new_name": new_name
    }

    await apply_or_wait(
        cmd, data, user_id, state, matches,
        "todo_task_modify_name",
        payload
    )


async def handle_task_delete(cmd, raw_msg: str, data: dict, user_id: int, state: T_State):
    content = re.sub(
        rf"^{re.escape(cmd_start)}todo\s+task\s+(?:-d|--delete)\s*",
        "",
        raw_msg,
        count=1
    ).strip()

    # task -d <任务名称> -n
    delete_note_only = content.endswith(" -n")

    if delete_note_only:
        task_name = content[:-3].strip()
    else:
        task_name = content.strip()

    if not task_name:
        if delete_note_only:
            await cmd.finish(f"格式: {cmd_start}todo task -d <任务名称> -n")
        await cmd.finish(f"格式: {cmd_start}todo task -d <任务名称>")

    matches = find_tasks(data, task_name)

    if not matches:
        await cmd.finish("未找到相关任务")

    action = "todo_task_delete_note" if delete_note_only else "todo_task_delete"

    await apply_or_wait(
        cmd, data, user_id, state, matches,
        action,
        {}
    )


async def handle_task_repeat(cmd, raw_msg: str, data: dict, user_id: int, state: T_State):
    content = re.sub(
        rf"^{re.escape(cmd_start)}todo\s+task+(?:-r|--routine)\s*",
        "",
        raw_msg,
        count=1
    )
    parts = content.split()

    if len(parts) < 3:
        await cmd.finish(f"格式: {cmd_start}todo task -r <任务名称> <频率> <次数>")

    count_text = parts[-1]
    freq = parts[-2]
    task_name = " ".join(parts[:-2]).strip()

    if freq not in ["每天", "每周", "每月"]:
        await cmd.finish("频率只能是：每天 / 每周 / 每月")

    if not count_text.isdigit():
        await cmd.finish("次数必须是数字")

    matches = find_tasks(data, task_name)

    if not matches:
        await cmd.finish("未找到相关任务")

    payload = {
        "repeat": {
            "frequency": freq,
            "count": int(count_text),
            "done_count": 0
        }
    }

    await apply_or_wait(
        cmd, data, user_id, state, matches,
        "todo_task_repeat",
        payload
    )


async def apply_or_wait(
    cmd,
    data: dict,
    user_id: int,
    state: T_State,
    matches: list,
    action: str,
    payload: dict
):
    if len(matches) == 1:
        await apply_task_action(
            cmd,
            data,
            user_id,
            matches[0],
            action,
            payload
        )
        return

    await ask_choice(
        cmd,
        state,
        action=action,
        candidates=matches,
        user_id=user_id,
        payload=payload,
        title="找到多个匹配项，请回复编号选择任务",
        formatter=format_todo_candidate,
    )


async def apply_task_action(
    cmd,
    data: dict,
    user_id: int,
    target_item: dict,
    action: str,
    payload: dict
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

    target_index = None
    target_task = None

    for i, task in enumerate(tasks):
        if task.get("id") == target_id:
            target_index = i
            target_task = task
            break

    if target_index is None or target_task is None:
        await cmd.finish("任务不存在，可能已被修改或删除")

    if action == "todo_task_modify_name":
        old_name = target_task["name"]

        push_history(
            data,
            action=f"修改任务名称: {old_name} → {payload['new_name']}"
        )

        target_task["name"] = payload["new_name"]
        save_todo(user_id, data)
        await cmd.finish(f"已修改任务名称: {target_task['name']}")

    elif action == "todo_task_modify_note":
        push_history(
            data,
            action=f"修改备注: {target_task['name']}"
        )

        target_task["note"] = payload["new_note"]
        save_todo(user_id, data)
        await cmd.finish(f"已修改任务备注: {target_task['name']}")

    elif action == "todo_task_delete":
        task_name = target_task["name"]

        push_history(
            data,
            action=f"删除任务: {task_name}"
        )

        del tasks[target_index]

        save_todo(user_id, data)
        await cmd.finish(f"已删除任务: {task_name}")

    elif action == "todo_task_delete_note":
        push_history(
            data,
            action=f"删除备注: {target_task['name']}"
        )

        target_task["note"] = ""
        save_todo(user_id, data)
        await cmd.finish(f"已删除任务备注: {target_task['name']}")

    elif action == "todo_task_repeat":
        push_history(
            data,
            action=f"添加周期提醒：{target_task['name']}"
        )

        target_task["repeat"] = payload["repeat"]
        save_todo(user_id, data)
        await cmd.finish(f"已添加周期提醒: {target_task['name']}")

    await cmd.finish("未知任务操作")


async def receive_task_choice(cmd, event: MessageEvent, state: T_State):
    action = state.get("pending_action")

    if action not in [
        "todo_task_modify_name",
        "todo_task_modify_note",
        "todo_task_delete",
        "todo_task_delete_note",
        "todo_task_repeat"
    ]:
        return False

    user_id = state["user_id"]
    payload = state.get("payload", {})

    _, target_item = await parse_choice(cmd, event, state)

    data = load_todo(user_id)
    await apply_task_action(
        cmd,
        data,
        user_id,
        target_item,
        action,
        payload,
    )

    return True