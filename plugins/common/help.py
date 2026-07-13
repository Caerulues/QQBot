import json
import io
from pathlib import Path

from PIL import Image, ImageDraw

from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment

from utils.recall_map import add
from config import config
from utils.font import load_font
from utils.build_help_image import render_image

HELP_PATH = Path(config.data_dir) / "help"
HELP_PATH.mkdir(parents=True, exist_ok=True)

help_cmd = on_command("help", priority=5, block=True)

def get_help_file():
    return HELP_PATH / "help.json"

def load_help_map() -> dict[str, list[str]]:
    file = get_help_file()

    if not file.exists():
        return {}

    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def get_help_lines(module: str = "") -> list[str]:
    help_map = load_help_map()
    module = module.strip().lower()

    return help_map.get(module, ["未找到该指令的帮助信息"])


def get_help(module: str = "") -> str:
    help_map = load_help_map()
    module = module.strip().lower()
    lines = get_help_lines(module)

    image_bytes = render_image(lines)

    return MessageSegment.image(image_bytes)


@help_cmd.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    module = args.extract_plain_text().strip()

    lines = get_help_lines(module)
    image_bytes = render_image(lines)

    sent = await help_cmd.send(MessageSegment.image(image_bytes))
    add(event.message_id, sent["message_id"])
    return