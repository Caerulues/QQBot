from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.typing import T_State

from storage.todo_storage import load_todo
from .branch import handle_branch
from .add import handle_add, receive_add_choice
from .done import handle_done, receive_done_choice
from .task import handle_task, receive_task_choice
from .revert import handle_revert
from plugins.common.help import get_help
from utils.pending_choice import handle_pending_choice

todo_cmd = on_command("todo", priority=5, block=True)

@todo_cmd.handle()
async def _(event: MessageEvent, state: T_State):
    handled = await handle_pending_choice(
        todo_cmd,
        event,
        state,
        [
            receive_done_choice,
            receive_task_choice,
            receive_add_choice,
        ]
    )

    if handled:
        return

    raw_msg = str(event.get_message()).strip()
    args = raw_msg.split()

    user_id = event.user_id
    data = load_todo(user_id)

    if len(args) < 2:
        await todo_cmd.finish(get_help("todo"))

    action = args[1]

    if action == "branch":
        await handle_branch(todo_cmd, args, raw_msg, data, user_id)

    elif action == "add":
        await handle_add(todo_cmd, args, raw_msg, data, user_id, state)

    elif action == "done":
        await handle_done(todo_cmd, args, raw_msg, data, user_id, state)

    elif action == "task":
        await handle_task(todo_cmd, args, raw_msg, data, user_id, state)

    elif action == "revert":
        await handle_revert(todo_cmd, data, user_id)

    elif action == "help":
        await todo_cmd.finish(get_help("todo"))

    else:
        await todo_cmd.finish("未知 todo 子命令")