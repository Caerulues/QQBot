from nonebot.typing import T_State


async def handle_pending_choice(
    cmd,
    event,
    state: T_State,
    handlers: list,
) -> bool:
    if "pending_action" not in state:
        return False

    for handler in handlers:
        handled = await handler(cmd, event, state)

        if handled:
            return True

    await cmd.finish("未知选择状态，请重新执行命令")