from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

from nonebot import get_bot, get_driver, on_command, on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageEvent
from nonebot.params import CommandArg
from nonebot.rule import is_type

from .config import BotConfig
from .manager import BridgeManager

config_path = Path(
    os.getenv(
        "MC_INTERCONNECTION_CONFIG",
        str(Path(__file__).resolve().parents[2]
            / "data"
            / "minecraft"
            / "minecraft_config.json"
            ),
    )
)
config = BotConfig.load(config_path)
manager = BridgeManager(config)
driver = get_driver()
server_task: asyncio.Task | None = None

mcservers = on_command("mcservers", priority=5, block=True)
mcinfo = on_command("mcinfo", priority=5, block=True)
run_server = on_command("run_server", priority=5, block=True)
stop_server = on_command("stop_server", priority=5, block=True)
qq_bridge = on_message(rule=is_type(GroupMessageEvent), priority=20, block=False)


def group_targets(mapping: dict[int, list[str]], group_id: int) -> list[str]:
    return mapping.get(int(group_id), [])


def sender_name(event: GroupMessageEvent) -> str:
    return (
        event.sender.card
        or event.sender.nickname
        or str(event.user_id)
    ).strip()


def clean_text(text: str) -> str:
    text = text.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()[:200]


async def send_to_groups(group_ids: list[int], text: str) -> None:
    bot = get_bot()
    for group_id in group_ids:
        try:
            await bot.send_group_msg(group_id=group_id, message=text)
        except Exception:
            continue


async def handle_agent_event(event: dict) -> None:
    if event.get("type") == "connection":
        return

    server_id = str(event.get("server_id", ""))
    server_name = str(event.get("server_name") or server_id)
    event_type = event.get("event")
    data = event.get("data", {})

    if event_type == "chat":
        group_ids = [
            group_id
            for group_id, server_ids in config.bridge_groups.items()
            if server_id in server_ids or "*" in server_ids
        ]
        text = (
            f"[MC][{server_name}] "
            f"{data.get('player', '未知')}: {data.get('message', '')}"
        )
    else:
        group_ids = [
            group_id
            for group_id, server_ids in config.event_groups.items()
            if server_id in server_ids or "*" in server_ids
        ]
        if event_type == "join":
            text = f"[MC][{server_name}] {data.get('player', '未知')} 加入了服务器"
        elif event_type == "leave":
            text = f"[MC][{server_name}] {data.get('player', '未知')} 离开了服务器"
        elif event_type == "death":
            text = f"[MC][{server_name}] {data.get('message', '')}"
        else:
            return

    await send_to_groups(group_ids, text)


manager.add_handler(handle_agent_event)


@driver.on_startup
async def start_bridge() -> None:
    global server_task
    server_task = asyncio.create_task(manager.serve_forever())


@driver.on_shutdown
async def stop_bridge() -> None:
    if server_task is not None:
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


@qq_bridge.handle()
async def forward_qq_to_minecraft(event: GroupMessageEvent) -> None:
    targets = group_targets(config.bridge_groups, event.group_id)
    if not targets or event.user_id == int(event.self_id):
        return

    raw = str(event.get_message()).strip()
    if not raw or "[CQ:" in raw:
        return

    if not config.forward_commands and (
        raw.startswith(config.command_start) or raw.startswith("/")
    ):
        return

    message = clean_text(raw)
    if message:
        await manager.send_chat(targets, sender_name(event), message)


@mcservers.handle()
async def handle_mcservers() -> None:
    servers = manager.list_servers()
    if not servers:
        await mcservers.finish("当前没有已连接服务器")

    lines = [
        f"{index}. {item['server_name']} ({item['server_id']})"
        for index, item in enumerate(servers, start=1)
    ]
    await mcservers.finish("已连接服务器：\n" + "\n".join(lines))


def default_server_id() -> str:
    servers = manager.list_servers()
    if len(servers) == 1:
        return servers[0]["server_id"]
    return ""


@mcinfo.handle()
async def handle_mcinfo(args: Message = CommandArg()) -> None:
    server_id = args.extract_plain_text().strip() or default_server_id()
    if not server_id:
        await mcinfo.finish(
            f"存在多台服务器，请使用 {config.command_start}mcinfo <server_id>"
        )

    try:
        response = await manager.call(server_id, "status", timeout=20)
    except KeyError:
        await mcinfo.finish(f"服务器未连接：{server_id}")
    except asyncio.TimeoutError:
        await mcinfo.finish("服务器响应超时")

    data = response.get("data", {})
    await mcinfo.finish(data.get("text") or response.get("error", "无法获取服务器信息"))


async def handle_control(
    matcher,
    event: MessageEvent,
    args: Message,
    action: str,
) -> None:
    if event.user_id not in config.admin_users:
        await matcher.finish("Process Denied")

    server_id = args.extract_plain_text().strip() or default_server_id()
    if not server_id:
        await matcher.finish("存在多台服务器，请指定 server_id")

    try:
        timeout = 60 if action == "stop_server" else 45
        response = await manager.call(server_id, action, timeout=timeout)
    except KeyError:
        await matcher.finish(f"服务器未连接：{server_id}")
    except asyncio.TimeoutError:
        await matcher.finish("服务器响应超时")

    data = response.get("data", {})
    await matcher.finish(data.get("message") or response.get("error", "操作失败"))


@run_server.handle()
async def handle_run_server(
    event: MessageEvent,
    args: Message = CommandArg(),
) -> None:
    await handle_control(run_server, event, args, "start_server")


@stop_server.handle()
async def handle_stop_server(
    event: MessageEvent,
    args: Message = CommandArg(),
) -> None:
    await handle_control(stop_server, event, args, "stop_server")
