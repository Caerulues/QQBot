import asyncio

from nonebot import get_driver, on_command
from nonebot.adapters.onebot.v11 import MessageEvent

from core.java_monitor import has_java_process
from core.terminal_control import (
    open_minecraft_terminal,
    restore_minecraft_window_id,
    stop_minecraft_terminal,
)
from core.terminal_state import clear_minecraft_window_id

from utils.recall_map import add
from utils.ipv6_monitor import start_ipv6_monitor, stop_ipv6_monitor


driver = get_driver()


from core.config import config

ALLOWED_USERS = config.qq.admin_users
SERVER_PATH = config.server.path
SERVER_COMMAND = config.server.command

minecraft_window_id = None


run_minecraft_server = on_command(
    "run_server",
    priority=5,
    block=True
)

stop_minecraft_server = on_command(
    "stop_server",
    priority=5,
    block=True
)


@driver.on_startup
async def restore_terminal_on_startup():
    global minecraft_window_id

    minecraft_window_id = await restore_minecraft_window_id()

    if minecraft_window_id:
        print(f"[server] 已恢复Minecraft Terminal窗口ID: {minecraft_window_id}")
    else:
        print("[server] 未找到可恢复的Minecraft Terminal窗口")


@run_minecraft_server.handle()
async def _(event: MessageEvent):
    global minecraft_window_id

    if event.user_id not in ALLOWED_USERS:
        sent = await run_minecraft_server.send("Process Denied")
        add(event.message_id, sent["message_id"])
        return

    # Bot 重启后，先尝试恢复旧窗口
    if not minecraft_window_id:
        minecraft_window_id = await restore_minecraft_window_id()

    if has_java_process():
        sent = await run_minecraft_server.send("Minecraft Server已在运行")
        add(event.message_id, sent["message_id"])

        if minecraft_window_id:
            await start_ipv6_monitor()

        return

    try:
        minecraft_window_id = await open_minecraft_terminal(
            SERVER_PATH,
            SERVER_COMMAND
        )

    except Exception as e:
        sent = await run_minecraft_server.send(
            f"Minecraft Server启动失败\n{e}"
        )
        add(event.message_id, sent["message_id"])
        return

    # 等待 Java 服务端进程出现
    for _ in range(20):
        if has_java_process():
            await start_ipv6_monitor()

            sent = await run_minecraft_server.send("Minecraft Server已启动")
            add(event.message_id, sent["message_id"])
            return

        await asyncio.sleep(1)

    sent = await run_minecraft_server.send(
        "Minecraft Server可能未成功启动：未检测到Java服务端进程"
    )
    add(event.message_id, sent["message_id"])


@stop_minecraft_server.handle()
async def _(event: MessageEvent):
    global minecraft_window_id

    if event.user_id not in ALLOWED_USERS:
        sent = await stop_minecraft_server.send("Process Denied")
        add(event.message_id, sent["message_id"])
        return

    if not minecraft_window_id:
        minecraft_window_id = await restore_minecraft_window_id()

    if not minecraft_window_id:
        sent = await stop_minecraft_server.send(
            "没有找到已绑定的Minecraft终端窗口"
        )
        add(event.message_id, sent["message_id"])
        return

    try:
        await stop_minecraft_terminal(
            minecraft_window_id,
            close_after_stop=True
        )

    except Exception as e:
        sent = await stop_minecraft_server.send(
            f"停止Minecraft Server失败\n{e}"
        )
        add(event.message_id, sent["message_id"])
        return

    # 等待 Java 进程消失
    for _ in range(15):
        if not has_java_process():
            stop_ipv6_monitor()
            clear_minecraft_window_id()
            minecraft_window_id = None

            sent = await stop_minecraft_server.send("Minecraft Server已停止")
            add(event.message_id, sent["message_id"])
            return

        await asyncio.sleep(1)

    sent = await stop_minecraft_server.send(
        "已发送stop命令，但仍检测到Java进程，请检查服务器是否卡住"
    )
    add(event.message_id, sent["message_id"])