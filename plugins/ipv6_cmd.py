from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent

from utils.recall_map import add
from core.ipv6 import get_ipv6

ipv6_cmd = on_command("ipv6", priority=5)

@ipv6_cmd.handle()
async def _(event: MessageEvent):
    ipv6 = get_ipv6()

    sent = await ipv6_cmd.send(f"{ipv6}")
    add(event.message_id, sent["message_id"])
    return