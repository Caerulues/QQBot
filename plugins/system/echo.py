from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent

from utils.recall_map import add
from utils.command import get_cmd_start

cmd_start = get_cmd_start()

echo = on_command("echo", priority=5, block=True)

@echo.handle()
async def handle_echo(event: MessageEvent):
    msg = str(event.get_message()).strip()
    content = msg.replace(f"{cmd_start}echo", "", 1).strip()

    sent = await echo.send(f"{content}")
    add(event.message_id, sent["message_id"])
    return