import time

from nonebot import on_command
from nonebot import get_bot
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import FinishedException

from utils.recall_map import add

ping = on_command("ping")

@ping.handle()
async def _(bot, event):
    receive_latency = (time.time() - event.time) * 1000
    start = time.perf_counter()
    await bot.send_private_msg(user_id=236885029, message="Testing ping...")
    send_latency = (time.perf_counter() - start) * 1000

    msg = await ping.send(f"接收延迟: {receive_latency:.2f}ms\n发送延迟: {send_latency:.2f}ms")
    add(event.message_id, msg["message_id"])
    return