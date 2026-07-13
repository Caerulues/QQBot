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
from config import config

BRIDGE_GROUP_ID = config.qq.bridge_group_id
RCON_HOST = config.rcon.host
RCON_PORT = config.rcon.port
RCON_PASSWORD = config.rcon.password
BOT_IDS = config.minecraft.bot_ids
IGNORE_PLAYER_IDS = config.minecraft.ignore_player_ids
MC_LOG_PATH = Path(config.minecraft.log_path)
QQ_TO_MC_PREFIX = "[QQ]"
FORWARD_BOT_SELF = False

# MARK: 工具函数

def clean_qq_text(text: str) -> str:
    text = text.replace("\r", " ").replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)

    if len(text) > 200:
        text = text[:200] + "..."

    return text

def clean_mc_text(text: str) -> str:
    text = re.sub(r"§.", "", text)
    return text.strip()

def get_group_display_name(event: GroupMessageEvent) -> str:
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
    bot = get_bot()
    await bot.send_group_msg(
        group_id=BRIDGE_GROUP_ID,
        message=f"[MC] {player_name}：{message}"
    )

# MARK: QQ -> Minecrafft

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

    # 不转发命令
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
        print(f"[mc_bridge] QQ -> MC 转发失败: {e}")

# MARK: Minecraft -> QQ

MC_CHAT_PATTERNS = [
    re.compile(r"^\[[^\]]+\] \[Server thread/INFO\]: <([^>]+)> (.*)$"),
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

            if msg.startswith(QQ_TO_MC_PREFIX):
                return None

            return name, msg

    return None

class LogTailer:
    def __init__(self, path: Path):
        self.path = path
        self.position = 0
        self.initialized = False

    def init_position(self):
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
            if player_name in BOT_IDS or player_name in IGNORE_PLAYER_IDS:
                continue
            await send_to_qq(player_name, message)

    except Exception as e:
        print(f"[mc_bridge] MC -> QQ 转发失败: {e}")