import uuid

from .revert import push_history
from .storage import save_todo
from .search import find_tasks
from core.parser import split_by_bar
from core.command import get_cmd_start

cmd_start = get_cmd_start()


async def handle_add(cmd, args: list[str], raw_msg: str, data: dict, user_id: int):
    if len(args) < 3:
        await cmd.finish(f"格式: {cmd_start}todo add -* <args1> | <args2>")

    sub = args[2]
    branches = data.setdefault("branches", {})

    # add -t <任务类名称> | <任务名称>
    if sub == "-t":
        content = raw_msg.replace(f"{cmd_start}todo add -t", "", 1).strip()
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
    elif sub == "-n":
        content = raw_msg.replace(f"{cmd_start}todo add -n", "", 1).strip()
        task_name, note = split_by_bar(content)

        if not task_name or not note:
            await cmd.finish(f"格式: {cmd_start}todo add -n <任务名称> | <任务备注>")

        matches = find_tasks(data, task_name)

        if not matches:
            await cmd.finish("未找到相关任务")

        if len(matches) > 1:
            msg = "找到多个匹配项，请使用更完整的任务名称:\n"
            msg += "\n".join(
                f"{i + 1}. {item['branch']} / {item['task']['name']}"
                for i, item in enumerate(matches)
            )
            await cmd.finish(msg)

        target = matches[0]["task"]
        target["note"] = note

        push_history(
            data,
            action=f"添加备注: {target['name']}"
        )
        save_todo(user_id, data)
        await cmd.finish(f"已添加备注: {target['name']}")

    else:
        await cmd.finish("未知 add 参数")