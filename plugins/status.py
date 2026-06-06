import time
import psutil

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message

from utils.recall_map import add

START_TIME = time.time()

status = on_command("status", priority=5, block=True)


def get_cpu():
    return psutil.cpu_percent(interval=0.5)


def get_memory():
    mem = psutil.virtual_memory()
    return mem.percent, mem.used / 1024 / 1024, mem.total / 1024 / 1024


def format_uptime(seconds: int) -> str:
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days} d")
    if hours > 0:
        parts.append(f"{hours} hr")
    if minutes > 0:
        parts.append(f"{minutes} min")
    parts.append(f"{seconds} s")

    return " ".join(parts)


@status.handle()
async def _(event):
    cpu = get_cpu()

    mem_percent, mem_used, mem_total = get_memory()

    elapsed = int(time.time() - START_TIME)

    msg = (
        f"CPU: {cpu:.2f}%\n"
        f"MEM: {mem_percent:.2f}% "
        f"({mem_used:.2f}/{mem_total:.2f} MB)\n"
        f"UPT: {format_uptime(elapsed)}"
    )

    sent = await status.send(f"{msg}")
    add(event.message_id, sent["message_id"])
    return