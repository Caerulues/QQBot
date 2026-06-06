import asyncio
import re
import time
from pathlib import Path

from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent

from mcstatus import JavaServer
from mcrcon import MCRcon

from utils.recall_map import add


mc_info = on_command(
    "mcinfo",
    aliases={"服务器信息", "信息", "serverinfo"},
    priority=5,
    block=True
)

from core.config import config

PING_TARGET = config.minecraft.ping_target
MC_STATUS_ADDRESS = config.minecraft.status_address
SERVER_NAME = config.minecraft.name

RCON_HOST = config.rcon.host
RCON_PORT = config.rcon.port
RCON_PASSWORD = config.rcon.password

MC_LOG_PATH = Path(config.minecraft.log_path)


# ===== 通用工具 =====

def clean_mc_color(text: str) -> str:
    """
    去掉 Minecraft 颜色代码，例如 §a、§c、§r。
    """
    return re.sub(r"§.", "", text).strip()

def run_rcon(command: str) -> str:
    with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT, timeout=5) as mcr:
        return mcr.command(command)


# ===== ping6出站延迟 =====

async def ping(target: str = "test6.ustc.edu.cn") -> str:
    """
    只发送 1 次 IPv6 ping，返回延迟文本。
    例如：23ms

    注意：这是服务器本机 -> 外网目标 的出站 IPv6 延迟，
    不是外网玩家 -> Minecraft服务器 的入站延迟。
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping6",
            "-c",
            "1",
            target,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return "超时"

        output = stdout.decode("utf-8", errors="ignore")
        error = stderr.decode("utf-8", errors="ignore")

        if proc.returncode != 0:
            print(f"[mc_info] ping6 once failed: {target}")
            print(error or output)
            return "未知"

        # macOS 常见：
        # 64 bytes from xxxx: icmp_seq=0 hlim=54 time=23.456 ms
        match = re.search(r"time[=<]([\d.]+)\s*ms", output)

        if match:
            return f"{round(float(match.group(1)))}"

        print(f"[mc_info] ping6 once parse failed: {target}")
        print(output)
        return "未知"

    except FileNotFoundError:
        print("[mc_info] ping6 command not found")
        return "未知"

    except Exception as e:
        print(f"[mc_info] ping6 once exception: {target}: {e}")
        return "未知"


# ===== 在线人数 / 玩家名 / 版本 / 本机握手延迟 =====

async def get_status_info():
    """
    返回：
    server_version, online, max_players, latency_ms, player_names
    """
    server = await JavaServer.async_lookup(MC_STATUS_ADDRESS, timeout=5)
    status = await server.async_status()

    server_version = status.version.name
    online = status.players.online
    max_players = status.players.max
    latency_ms = await ping(PING_TARGET)

    player_names = []

    if status.players.sample:
        player_names = [player.name for player in status.players.sample]

    return server_version, online, max_players, latency_ms, player_names


# ===== TPS / MSPT =====

def parse_spark_tps(text: str) -> tuple[str, str]:
    text = clean_mc_color(text)

    # 去掉日志前缀，例如：
    # [21:24:18] [spark-worker-pool-1-thread-3/INFO]: [⚡]
    lines = []
    for line in text.splitlines():
        line = re.sub(r"^\[[^\]]+\] \[[^\]]+\]:\s*", "", line)
        line = line.replace("[⚡]", "").strip()
        if line:
            lines.append(line)

    tps = "未知"
    mspt = "未知"

    for i, line in enumerate(lines):
        # 找到 TPS 标题行，下一行就是 TPS 数字列表
        if "TPS from last" in line:
            if i + 1 < len(lines):
                tps_line = lines[i + 1]

                # 例：20.0, 20.0, 20.0, *20.0, 20.0
                nums = re.findall(r"\*?([0-9]+(?:\.[0-9]+)?)", tps_line)
                if nums:
                    tps = nums[0]

        # 找到 Tick durations 标题行，下一行就是 MSPT 数字列表
        if "Tick durations" in line:
            if i + 1 < len(lines):
                mspt_line = lines[i + 1]

                # 例：8.5/9.8/12.0/18.9;  8.4/9.6/12.0/22.0
                groups = re.findall(
                    r"([0-9]+(?:\.[0-9]+)?)/([0-9]+(?:\.[0-9]+)?)/([0-9]+(?:\.[0-9]+)?)/([0-9]+(?:\.[0-9]+)?)",
                    mspt_line
                )

                if groups:
                    first_group = groups[0]

                    # min / med / 95%ile / max
                    # 这里取 med，也就是第二个值
                    mspt = first_group[1]

    return tps, mspt


def read_log_from_position(position: int) -> tuple[str, int]:
    if not MC_LOG_PATH.exists():
        return "", position

    with MC_LOG_PATH.open("r", encoding="utf-8", errors="ignore") as f:
        f.seek(position)
        text = f.read()
        new_position = f.tell()

    return text, new_position


async def get_tps_mspt_info():
    """
    通过 RCON 调用 spark tps 并解析日志。
    若 RCON 不可用、spark 未安装或日志不可读，不影响基础在线信息展示。
    """
    if MC_LOG_PATH.exists():
        start_position = MC_LOG_PATH.stat().st_size
    else:
        start_position = 0

    try:
        response = run_rcon("spark tps")
    except Exception as e:
        print(f"[mc_info] RCON/spark unavailable: {e}")
        return "未知", "未知"

    if response and any(key in clean_mc_color(response).lower() for key in ["unknown", "not found", "不存在"]):
        print(f"[mc_info] spark command unavailable: {response}")
        return "未知", "未知"

    # spark tps 是异步输出，稍微等一下日志写入
    await asyncio.sleep(1.5)

    try:
        text, _ = read_log_from_position(start_position)
    except Exception as e:
        print(f"[mc_info] read spark log failed: {e}")
        return "未知", "未知"

    tps, mspt = parse_spark_tps(text)
    return tps, mspt


# ===== 输出格式 =====

def format_player_names(player_names: list[str]) -> str:
    anonymous_count = 0
    normal_players = []

    for name in player_names:
        if name == "Anonymous Player":
            anonymous_count += 1
        else:
            normal_players.append(name)

    parts = []

    if normal_players:
        parts.extend(normal_players)

    if anonymous_count > 0:
        parts.append(f"[{anonymous_count}个匿名玩家]")

    if not parts:
        parts.append("当前无玩家在线")

    return f"◤ {', '.join(parts)} ◢"


def format_mc_info(
    server_version: str,
    online: int,
    max_players: int,
    latency_ms: int,
    tps: str,
    mspt: str,
    player_names: list[str]
) -> str:
    players_text = format_player_names(player_names)

    return (
        f"{SERVER_NAME}({server_version})\n"
        f"在线: {online}/{max_players} 出站延迟: {latency_ms}ms\n"
        f"TPS: {tps}, MSPT: {mspt}\n"
        f"{players_text}"
    )

@mc_info.handle()
async def _(event: MessageEvent):
    try:
        status_task = get_status_info()
        perf_task = get_tps_mspt_info()

        (
            server_version,
            online,
            max_players,
            latency_ms,
            player_names
        ), (
            tps,
            mspt
        ) = await asyncio.gather(status_task, perf_task)

        msg = format_mc_info(
            server_version=server_version,
            online=online,
            max_players=max_players,
            latency_ms=latency_ms,
            tps=tps,
            mspt=mspt,
            player_names=player_names
        )

    except Exception as e:
        msg = (
            "无法获取Minecraft服务器信息。\n"
            f"错误信息：{e}\n"
        )

    sent = await mc_info.send(msg)
    add(event.message_id, sent["message_id"])