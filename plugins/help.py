import json

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from pathlib import Path

from utils.recall_map import add
from core.config import config

HELP_PATH = Path(config.data_dir) / "help"
HELP_PATH.mkdir(parents=True, exist_ok=True)

def get_help_file():
    return HELP_PATH / "help.json"

def load_help_map() -> dict[str, list[str]]:
    file = get_help_file()

    if not file.exists():
        return ""

    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

HELP_MAP = load_help_map()

def get_help(module: str = "") -> str:
    return "\n".join(
        HELP_MAP.get(module.lower(), ["未找到该指令的帮助信息"])
    )

help_cmd = on_command("help", priority=5, block=True)

@help_cmd.handle()
async def _(event: MessageEvent):
    args = event.get_plaintext().replace(".help", "").strip()

    sent = await help_cmd.send(get_help(args))
    add(event.message_id, sent["message_id"])
    return