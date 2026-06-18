import json
import uuid

from PIL import Image, ImageDraw, ImageFont
import io
import textwrap

from pathlib import Path
from datetime import datetime

from nonebot import on_command, require, get_bot
from nonebot.adapters.onebot.v11 import (
    Bot,
    Message,
    GroupMessageEvent,
    MessageSegment
)
from nonebot.rule import is_type

require("nonebot_plugin_apscheduler")

from nonebot_plugin_apscheduler import scheduler

from utils.recall_map import add
from plugins.help import get_help

from core.config import config

DATA_PATH = Path(config.data_dir) / "todo_list.json"
DATA_PATH.mkdir(parents=True, exist_ok=True)

todolist_cmd = on_command("todo", priority=5, block=True)


