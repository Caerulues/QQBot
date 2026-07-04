import json
import re
from pathlib import Path
from typing import Optional

from nonebot import get_bot, logger, require

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

from core.config import config


# MARK: 配置

GROUP_ID = config.qq.event_group_id
MC_LOG_PATH = Path(config.minecraft.log_path)

JOB_ID = "minecraft_event_monitor"
CHECK_INTERVAL_SECONDS = 1

MC_PREFIX = "[MC]"
TRANSLATE_DEATH_MESSAGE = config.minecraft.translate_message

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEATH_MESSAGES_PATH = PROJECT_ROOT / "data" / "minecraft" / "assets" / "death_messages.json"
CREATURE_PATH = PROJECT_ROOT / "data" / "minecraft" / "assets" / "creature.json"


# MARK: 玩家状态

ONLINE_PLAYERS: set[str] = set()


# MARK: 文本处理

def clean_mc_text(text: str) -> str:
    return re.sub(r"§.", "", text).strip()


def strip_log_prefix(line: str) -> str:
    line = clean_mc_text(line)

    line = re.sub(r"^\[[^\]]+\] \[[^\]]+\]:\s*", "", line)
    line = re.sub(r"^\[[^\]]+\]:\s*", "", line)

    return line.strip()


def is_player_name(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_]{1,16}", name))


def normalize_death_text(text: str) -> str:
    return text.strip()


# MARK: 死亡消息翻译

def load_json_dict(path: Path, name: str) -> dict[str, str]:
    if not path.exists():
        logger.warning(f"{name} 文件不存在: {path}")
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            logger.warning(f"{name} 格式错误：根对象应为 dict")
            return {}

        return data

    except Exception as e:
        logger.warning(f"读取 {name} 失败: {e}")
        return {}


def template_to_regex(template: str) -> re.Pattern:
    """
    将 Minecraft 死亡消息模板转换为正则。

    示例：
    %1$s was slain by %2$s
    ->
    (?P<p1>.+?) was slain by (?P<p2>.+?)
    """
    parts = re.split(r"(%[123]\$s|%s)", template)

    pattern = ""

    for part in parts:
        if part == "%1$s":
            pattern += r"(?P<p1>.+?)"
        elif part == "%2$s":
            pattern += r"(?P<p2>.+?)"
        elif part == "%3$s":
            pattern += r"(?P<p3>.+?)"
        elif part == "%s":
            pattern += r"(?P<p>.+?)"
        else:
            pattern += re.escape(part)

    return re.compile(f"^{pattern}$")


DEATH_MESSAGES = load_json_dict(DEATH_MESSAGES_PATH, "death_messages.json")
CREATURE_MESSAGES = load_json_dict(CREATURE_PATH, "creature.json")

DEATH_PATTERNS: list[tuple[re.Pattern, str]] = [
    (template_to_regex(en), zh)
    for en, zh in DEATH_MESSAGES.items()
]


def match_death_message(msg: str) -> Optional[tuple[re.Match, str]]:
    msg = normalize_death_text(msg)

    for pattern, zh_template in DEATH_PATTERNS:
        match = pattern.match(msg)

        if match:
            return match, zh_template

    return None


def translate_mc_name(name: str) -> str:
    return CREATURE_MESSAGES.get(name, name)

def translate_death_message(msg: str) -> Optional[str]:
    matched = match_death_message(msg)

    if not matched:
        return None

    match, zh_template = matched
    result = zh_template

    for name, value in match.groupdict().items():
        if value is None:
            continue

        # p1 是死亡主体，通常是玩家名
        # p2 / p3 可能是实体名或物品名
        if name != "p1":
            value = translate_mc_name(value)

        if name.startswith("p") and name[1:].isdigit():
            result = result.replace(f"%{name[1:]}$s", value)
        elif name == "p":
            result = result.replace("%s", value)

    return result


def get_death_victim(msg: str) -> Optional[str]:
    matched = match_death_message(msg)

    if not matched:
        return None

    match, _ = matched
    victim = match.groupdict().get("p1")

    if victim and is_player_name(victim):
        return victim

    return None


def is_player_death_message(msg: str) -> bool:
    victim = get_death_victim(msg)

    if victim is None:
        return False

    return victim in ONLINE_PLAYERS


# MARK: 服务器消息处理

JOIN_PATTERN = re.compile(r"^([A-Za-z0-9_]{1,16}) joined the game$")
LEAVE_PATTERN = re.compile(r"^([A-Za-z0-9_]{1,16}) left the game$")


def parse_mc_event(line: str) -> Optional[str]:
    msg = strip_log_prefix(line)

    if not msg:
        return None

    if msg.startswith("[⚡]"):
        return None

    if "RCON Client" in line:
        return None

    ignored_prefixes = (
        "Thread ",
        "Saving ",
        "Saved ",
        "Time elapsed:",
        "Done ",
        "Starting ",
        "Stopping ",
        "Loading ",
        "Preparing ",
        "Unknown command",
        "There are ",
        "Found ",
        "Disconnecting ",
        "UUID of player ",
        "Player ",
        "com.mojang",
        "net.minecraft",
        "java.",
    )

    if msg.startswith(ignored_prefixes):
        return None

    join_match = JOIN_PATTERN.match(msg)
    if join_match:
        name = join_match.group(1)
        ONLINE_PLAYERS.add(name)
        return f"{MC_PREFIX} {name} 加入了服务器"

    leave_match = LEAVE_PATTERN.match(msg)
    if leave_match:
        name = leave_match.group(1)
        ONLINE_PLAYERS.discard(name)
        return f"{MC_PREFIX} {name} 离开了服务器"

    if is_player_death_message(msg):
        if TRANSLATE_DEATH_MESSAGE:
            translated = translate_death_message(msg)

            if translated:
                return f"{MC_PREFIX} {translated}"

        return f"{MC_PREFIX} {msg}"

    return None


# MARK: log 读取

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

        if current_size < self.position:
            self.position = 0

        with self.path.open("r", encoding="utf-8", errors="ignore") as f:
            f.seek(self.position)
            lines = f.readlines()
            self.position = f.tell()

        return lines


tailer = LogTailer(MC_LOG_PATH)


async def check_minecraft_events():
    if GROUP_ID is None:
        return

    try:
        lines = tailer.read_new_lines()

        if not lines:
            return

        bot = get_bot()

        for line in lines:
            message = parse_mc_event(line)

            if not message:
                continue

            await bot.send_group_msg(
                group_id=GROUP_ID,
                message=message
            )

    except Exception as e:
        logger.warning(f"Minecraft事件转发失败: {e}")


if scheduler.get_job(JOB_ID):
    scheduler.remove_job(JOB_ID)

scheduler.add_job(
    check_minecraft_events,
    "interval",
    seconds=CHECK_INTERVAL_SECONDS,
    id=JOB_ID,
)