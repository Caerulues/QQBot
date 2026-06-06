import asyncio
import os
import platform
import subprocess

from nonebot import get_driver, on_command, logger
from nonebot.adapters.onebot.v11 import MessageEvent
from mcrcon import MCRcon

from core.java_monitor import has_java_process
from core.terminal_control import (
    is_macos,
    open_minecraft_terminal,
    restore_minecraft_window_id,
    stop_minecraft_terminal,
)
from core.terminal_state import (
    clear_minecraft_pid,
    clear_minecraft_state,
    clear_minecraft_window_id,
    load_minecraft_pid,
    save_minecraft_pid,
)
from utils.recall_map import add
from utils.ipv6_monitor import start_ipv6_monitor, stop_ipv6_monitor
from core.config import config


driver = get_driver()

ALLOWED_USERS = config.qq.admin_users
SERVER_PATH = config.server.path
SERVER_COMMAND = config.server.command
SERVER_LAUNCH_MODE = config.server.launch_mode.lower()

minecraft_window_id = None

run_minecraft_server = on_command("run_server", priority=5, block=True)
stop_minecraft_server = on_command("stop_server", priority=5, block=True)


def get_launch_mode() -> str:
    """
    auto: macOS 使用 Terminal；其他系统使用 subprocess。
    terminal: 强制 macOS Terminal。
    subprocess: 跨平台后台子进程。
    """
    if SERVER_LAUNCH_MODE in {"terminal", "subprocess"}:
        return SERVER_LAUNCH_MODE
    return "terminal" if is_macos() else "subprocess"


def is_process_alive(pid: int | None) -> bool:
    if not pid:
        return False

    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


async def open_minecraft_subprocess(server_path: str, command: str) -> int:
    if not server_path or not command:
        raise RuntimeError("server.path 或 server.command 未配置")

    proc = subprocess.Popen(
        command,
        cwd=server_path,
        shell=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=(platform.system() != "Windows"),
        creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == "Windows" else 0),
    )
    save_minecraft_pid(proc.pid)
    return proc.pid


async def send_stop_by_rcon() -> bool:
    if not config.rcon.password:
        return False

    try:
        def _stop():
            with MCRcon(
                config.rcon.host,
                config.rcon.password,
                port=config.rcon.port,
                timeout=5,
            ) as mcr:
                mcr.command("stop")

        await asyncio.to_thread(_stop)
        return True
    except Exception as e:
        logger.warning(f"RCON stop failed: {e}")
        return False


async def wait_until_java_running(seconds: int = 20) -> bool:
    for _ in range(seconds):
        if has_java_process():
            return True
        await asyncio.sleep(1)
    return False


async def wait_until_java_stopped(seconds: int = 20) -> bool:
    for _ in range(seconds):
        if not has_java_process():
            return True
        await asyncio.sleep(1)
    return False


@driver.on_startup
async def restore_server_state_on_startup():
    global minecraft_window_id

    if is_macos():
        minecraft_window_id = await restore_minecraft_window_id()
        if minecraft_window_id:
            logger.info(f"[server] 已恢复Minecraft Terminal窗口ID: {minecraft_window_id}")
        else:
            logger.info("[server] 未找到可恢复的Minecraft Terminal窗口")

    saved_pid = load_minecraft_pid()
    if saved_pid and is_process_alive(saved_pid):
        logger.info(f"[server] 已恢复Minecraft子进程PID: {saved_pid}")

    # 即使服务器不是本次 Bot 通过 .run_server 启动，只要检测到 Java 服务端进程，IPv6 监控也会启动。
    if has_java_process():
        await start_ipv6_monitor(force_send=False)


@run_minecraft_server.handle()
async def _(event: MessageEvent):
    global minecraft_window_id

    if event.user_id not in ALLOWED_USERS:
        sent = await run_minecraft_server.send("Process Denied")
        add(event.message_id, sent["message_id"])
        return

    if has_java_process():
        await start_ipv6_monitor(force_send=True)
        sent = await run_minecraft_server.send("Minecraft Server已在运行，IPv6监控已启动")
        add(event.message_id, sent["message_id"])
        return

    try:
        mode = get_launch_mode()

        if mode == "terminal":
            minecraft_window_id = await open_minecraft_terminal(SERVER_PATH, SERVER_COMMAND)
        else:
            pid = await open_minecraft_subprocess(SERVER_PATH, SERVER_COMMAND)
            logger.info(f"[server] Minecraft subprocess started, pid={pid}")

    except Exception as e:
        sent = await run_minecraft_server.send(f"Minecraft Server启动失败\n{e}")
        add(event.message_id, sent["message_id"])
        return

    if await wait_until_java_running(20):
        await start_ipv6_monitor(force_send=True)
        sent = await run_minecraft_server.send("Minecraft Server已启动")
        add(event.message_id, sent["message_id"])
        return

    sent = await run_minecraft_server.send("Minecraft Server可能未成功启动：未检测到Java服务端进程")
    add(event.message_id, sent["message_id"])


@stop_minecraft_server.handle()
async def _(event: MessageEvent):
    global minecraft_window_id

    if event.user_id not in ALLOWED_USERS:
        sent = await stop_minecraft_server.send("Process Denied")
        add(event.message_id, sent["message_id"])
        return

    if not has_java_process():
        stop_ipv6_monitor()
        clear_minecraft_state()
        minecraft_window_id = None
        sent = await stop_minecraft_server.send("Minecraft Server未在运行")
        add(event.message_id, sent["message_id"])
        return

    stopped_command_sent = False
    errors = []

    # 先尝试 macOS Terminal。若窗口被手动关闭，则按标题恢复；恢复失败后改用 RCON。
    if is_macos():
        if not minecraft_window_id:
            minecraft_window_id = await restore_minecraft_window_id()

        if minecraft_window_id:
            try:
                await stop_minecraft_terminal(minecraft_window_id, close_after_stop=True)
                stopped_command_sent = True
            except Exception as e:
                errors.append(f"Terminal停止失败: {e}")
                clear_minecraft_window_id()
                minecraft_window_id = None

    if not stopped_command_sent:
        stopped_command_sent = await send_stop_by_rcon()

    if not stopped_command_sent:
        detail = "\n".join(errors) if errors else "未找到可用的Terminal窗口，且RCON停止失败或未配置"
        sent = await stop_minecraft_server.send(f"停止Minecraft Server失败\n{detail}")
        add(event.message_id, sent["message_id"])
        return

    if await wait_until_java_stopped(20):
        stop_ipv6_monitor()
        clear_minecraft_state()
        minecraft_window_id = None
        sent = await stop_minecraft_server.send("Minecraft Server已停止")
        add(event.message_id, sent["message_id"])
        return

    clear_minecraft_pid()
    sent = await stop_minecraft_server.send("已发送stop命令，但仍检测到Java进程，请检查服务器是否卡住")
    add(event.message_id, sent["message_id"])
