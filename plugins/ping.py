import time

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent

from utils.recall_map import add
from core.config import config

ping = on_command("ping", priority=5, block=True)


async def send_ping_probe(bot: Bot, event: MessageEvent):
    """
    在当前会话发送测试消息，避免硬编码私聊 QQ 号。
    如需继续使用固定私聊目标，可在 config.toml 中增加 [qq].ping_user_id。
    """
    target_user = getattr(config.qq, "ping_user_id", None)

    if target_user:
        return await bot.send_private_msg(user_id=target_user, message="Testing ping...")

    return await bot.send(event, "Testing ping...")


@ping.handle()
async def _(bot: Bot, event: MessageEvent):
    receive_latency = (time.time() - event.time) * 1000

    start = time.perf_counter()
    probe = await send_ping_probe(bot, event)
    send_latency = (time.perf_counter() - start) * 1000

    if isinstance(probe, dict) and "message_id" in probe:
        add(event.message_id, probe["message_id"])

    msg = await ping.send(
        f"接收延迟: {receive_latency:.2f}ms\n"
        f"发送延迟: {send_latency:.2f}ms"
    )
    add(event.message_id, msg["message_id"])
