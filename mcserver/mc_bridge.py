import asyncio
import json
import re
from pathlib import Path
from typing import Optional

from nonebot import get_bot, on_message, require
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.rule import is_type

from mcrcon import MCRcon

require("nonebot_plugin_apscheduler")

from nonebot_plugin_apscheduler import scheduler

# ===== 基本配置 =====

from core.config import config

BRIDGE_GROUP_ID = config.qq.bridge_group_id

RCON_HOST = config.rcon.host
RCON_PORT = config.rcon.port
RCON_PASSWORD = config.rcon.password

MC_LOG_PATH = Path(config.minecraft.log_path)

# 防止 QQ->MC 后又被 latest.log 识别为 MC->QQ 的前缀
QQ_TO_MC_PREFIX = "[QQ]"

# 是否转发机器人自己发的群消息
FORWARD_BOT_SELF = False


# ===== 工具函数 =====

def clean_qq_text(text: str) -> str:
    """
    清理 QQ 消息，避免换行和过长文本破坏 MC 聊天显示。
    """
    text = text.replace("\r", " ").replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)

    if len(text) > 200:
        text = text[:200] + "..."

    return text


def clean_mc_text(text: str) -> str:
    """
    清理 Minecraft 日志中的颜色代码。
    """
    text = re.sub(r"§.", "", text)
    return text.strip()


def get_group_display_name(event: GroupMessageEvent) -> str:
    """
    优先使用群名片，其次昵称，最后 QQ 号。
    """
    sender = event.sender

    card = getattr(sender, "card", "") or ""
    nickname = getattr(sender, "nickname", "") or ""

    if card.strip():
        return card.strip()

    if nickname.strip():
        return nickname.strip()

    return str(event.user_id)


def run_rcon(command: str) -> str:
    with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT, timeout=5) as mcr:
        return mcr.command(command)


async def send_to_minecraft(name: str, message: str):
    """
    用 tellraw 向所有 Minecraft 玩家发送 QQ 消息。
    使用 json.dumps 避免引号、反斜杠等字符破坏 JSON。
    """
    payload = [
        {
            "text": f"{QQ_TO_MC_PREFIX} ",
            "color": "aqua"
        },
        {
            "text": f"{name}",
            "color": "yellow"
        },
        {
            "text": "：",
            "color": "white"
        },
        {
            "text": message,
            "color": "white"
        }
    ]

    command = f"tellraw @a {json.dumps(payload, ensure_ascii=False)}"
    run_rcon(command)


async def send_to_qq(player_name: str, message: str):
    """
    把 Minecraft 消息发到 QQ 群。
    """
    bot = get_bot()
    await bot.send_group_msg(
        group_id=BRIDGE_GROUP_ID,
        message=f"[MC] {player_name}：{message}"
    )


# ===== QQ -> Minecraft =====

qq_to_mc = on_message(
    rule=is_type(GroupMessageEvent),
    priority=20,
    block=False
)


@qq_to_mc.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    if BRIDGE_GROUP_ID is None:
        return

    if event.group_id != BRIDGE_GROUP_ID:
        return

    if not FORWARD_BOT_SELF and event.user_id == int(event.self_id):
        return

    raw_msg = str(event.get_message()).strip()

    if not raw_msg:
        return

    # 不转发命令，避免 .help、.ddl、.run_server 等进入 MC
    if raw_msg.startswith(".") or raw_msg.startswith("/"):
        return

    # 简单跳过 CQ 码消息，比如图片、表情、at 等
    if "[CQ:" in raw_msg:
        return

    name = get_group_display_name(event)
    msg = clean_qq_text(raw_msg)

    if not msg:
        return

    try:
        await send_to_minecraft(name, msg)
    except Exception as e:
        # 不建议每次都往群里报错，否则服务器关闭时会刷屏
        print(f"[mc_bridge] QQ -> MC 转发失败: {e}")


# ===== Minecraft -> QQ =====

MC_CHAT_PATTERNS = [
    # 常见 Vanilla / Paper 日志格式：
    # [12:34:56] [Server thread/INFO]: <Steve> hello
    re.compile(r"^\[[^\]]+\] \[Server thread/INFO\]: <([^>]+)> (.*)$"),

    # 有些服务端日志可能没有前面的时间：
    # [Server thread/INFO]: <Steve> hello
    re.compile(r"^\[Server thread/INFO\]: <([^>]+)> (.*)$"),
]


def parse_mc_chat_line(line: str) -> Optional[tuple[str, str]]:
    line = clean_mc_text(line)

    for pattern in MC_CHAT_PATTERNS:
        match = pattern.match(line)
        if match:
            name = match.group(1).strip()
            msg = match.group(2).strip()

            if not name or not msg:
                return None

            # 避免 QQ->MC 的 tellraw 消息又回流到 QQ
            if msg.startswith(QQ_TO_MC_PREFIX):
                return None

            return name, msg

    return None


class LogTailer:
    """
    简单的 latest.log 增量读取器。
    每次只读取新增内容。
    """

    def __init__(self, path: Path):
        self.path = path
        self.position = 0
        self.initialized = False

    def init_position(self):
        """
        启动时跳到文件末尾，避免把历史聊天记录重新发到 QQ。
        """
        if self.path.exists():
            self.position = self.path.stat().st_size
        else:
            self.position = 0

        self.initialized = True

    def read_new_lines(self) -> list[str]:
        if not self.initialized:
            self.init_position()
            return []

        if not self.path.exists():
            self.position = 0
            return []

        current_size = self.path.stat().st_size

        # latest.log 被重建或截断时，重新从头读
        if current_size < self.position:
            self.position = 0

        lines = []

        with self.path.open("r", encoding="utf-8", errors="ignore") as f:
            f.seek(self.position)
            lines = f.readlines()
            self.position = f.tell()

        return lines


tailer = LogTailer(MC_LOG_PATH)


@scheduler.scheduled_job("interval", seconds=1, id="mc_bridge_log_tailer")
async def check_minecraft_chat_log():
    try:
        lines = tailer.read_new_lines()

        for line in lines:
            parsed = parse_mc_chat_line(line)

            if not parsed:
                continue

            player_name, message = parsed
            await send_to_qq(player_name, message)

    except Exception as e:
        print(f"[mc_bridge] MC -> QQ 转发失败: {e}")