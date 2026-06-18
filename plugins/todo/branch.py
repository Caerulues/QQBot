from .storage import save_todo
from .revert import push_history
from core.parser import split_by_bar
from core.command import get_cmd_start
from utils.render_image import render_image
from nonebot.adapters.onebot.v11 import MessageSegment

cmd_start = get_cmd_start()

async def handle_branch(cmd, args: list[str], raw_msg: str, data: dict, user_id: int):
    if len(args) < 3:
        await cmd.finish(f"格式：{cmd_start}todo branch <任务类名称>")

    sub = args[2]
    branches = data.setdefault("branches", {})

    if sub == "-a":
        if not branches:
            await cmd.finish("当前没有任务类")

        lines = [
            "全部任务类",
            ""
        ]

        for name, tasks in branches.items():
            undone = sum(1 for task in tasks if not task.get("done"))
            done = len(tasks) - undone

            lines.append(
                f"{name} - 共 {len(tasks)} 个任务，未完成 {undone} 个，已完成 {done} 个"
            )

        image_bytes = render_image(lines)
        await cmd.finish(MessageSegment.image(image_bytes))


    elif sub == "-l":
        content = raw_msg.replace(f"{cmd_start}todo branch -l", "", 1).strip()

        if not content:
            await cmd.finish(f"格式：{cmd_start}todo branch -l <任务类名称>")

        branch_name = content

        if branch_name not in branches:
            await cmd.finish("任务类不存在")

        tasks = branches[branch_name]

        lines = [
            f"任务类：{branch_name}",
            ""
        ]

        if not tasks:
            lines.append("暂无任务")

        else:
            for i, task in enumerate(tasks):
                note = task.get("note", "")
                left = f"{i + 1}. {task['name']}"

                if note:
                    right = f"{"已完成" if task.get('done') else "未完成"} | 备注: {note}"

                else:
                    right = f"{"已完成" if task.get('done') else "未完成"}"

                lines.append(f"{left} - {right}")

        image_bytes = render_image(lines)
        await cmd.finish(MessageSegment.image(image_bytes))

    elif sub == "-m":
        content = raw_msg.replace(f"{cmd_start}todo branch -m", "", 1).strip()
        old_name, new_name = split_by_bar(content)

        if not old_name or not new_name:
            await cmd.finish(
                f"格式：{cmd_start}todo branch -m <原任务类名称> | <新任务类名称>"
            )

        if old_name not in branches:
            await cmd.finish("原任务类不存在")

        if new_name in branches:
            await cmd.finish("新任务类名称已存在")

        push_history(
            data,
            action=f"修改任务类：{old_name} → {new_name}"
        )
        branches[new_name] = []
        save_todo(user_id, data)
        branches[new_name] = branches.pop(old_name)
        save_todo(user_id, data)
        await cmd.finish(f"已将任务类 {old_name} 改名为 {new_name}")

    elif sub == "-d":
        content = raw_msg.replace(f"{cmd_start}todo branch -d", "", 1).strip()

        if not content:
            await cmd.finish(f"格式：{cmd_start}todo branch -d <任务类名称>")

        branch_name = content

        if branch_name not in branches:
            await cmd.finish("任务类不存在")

        push_history(
            data,
            action=f"删除任务类：{branch_name}"
        )
        branches.pop(branch_name)
        save_todo(user_id, data)
        await cmd.finish(f"已删除任务类：{branch_name}")

    else:
        content = raw_msg.replace(f"{cmd_start}todo branch", "", 1).strip()

        if not content:
            await cmd.finish(f"格式：{cmd_start}todo branch <任务类名称>")

        branch_name = content

        if branch_name in branches:
            await cmd.finish("任务类已存在")

        push_history(
            data,
            action=f"创建任务类：{branch_name}"
        )
        branches[branch_name] = []
        save_todo(user_id, data)
        await cmd.finish(f"已创建任务类：{branch_name}")