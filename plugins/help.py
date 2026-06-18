import json
import io
import platform
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment

from utils.recall_map import add
from core.config import config
from core.font import load_font

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

def split_help_line(line: str) -> tuple[str, str]:
    if " - " in line:
        left, right = line.split(" - ", 1)
        return left.strip(), right.strip()

    return line.strip(), ""

def wrap_text(text: str, font, max_width: int) -> list[str]:
    if not text:
        return [""]

    lines = []
    current = ""

    for char in text:
        test = current + char
        bbox = font.getbbox(test)
        width = bbox[2] - bbox[0]

        if width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = char

    if current:
        lines.append(current)

    return lines

def render_help_image(lines: list[str]) -> bytes:
    title_font = load_font(34)
    section_font = load_font(30)
    cmd_font = load_font(25)
    desc_font = load_font(24)

    padding = 36
    width = 1100
    content_width = width - padding * 2
    row_padding = 18
    line_gap = 8
    block_gap = 14

    rows = []

    for line in lines:
        if line == "":
            rows.append(("blank", "", "", 18))
            continue

        left, right = split_help_line(line)

        if right == "":
            rows.append(("section", left, "", 54))
        else:
            cmd_lines = wrap_text(left, cmd_font, content_width - row_padding * 2)
            desc_lines = wrap_text(right, desc_font, content_width - row_padding * 2)

            cmd_h = len(cmd_lines) * 30 + max(0, len(cmd_lines) - 1) * line_gap
            desc_h = len(desc_lines) * 28 + max(0, len(desc_lines) - 1) * line_gap

            height = row_padding * 2 + cmd_h + 8 + desc_h
            rows.append(("row", cmd_lines, desc_lines, height))

    height = padding * 2 + sum(row[3] for row in rows) + block_gap * len(rows)

    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    y = padding

    for row in rows:
        row_type = row[0]
        row_height = row[3]

        if row_type == "blank":
            y += row_height
            continue

        if row_type == "section":
            draw.rectangle(
                [padding, y, width - padding, y + row_height],
                fill=(235, 235, 235),
                outline=(180, 180, 180)
            )
            draw.text(
                (padding + row_padding, y + 10),
                row[1],
                font=section_font,
                fill=(20, 20, 20)
            )
            y += row_height + block_gap
            continue

        cmd_lines = row[1]
        desc_lines = row[2]

        draw.rectangle(
            [padding, y, width - padding, y + row_height],
            fill=(255, 255, 255),
            outline=(200, 200, 200)
        )

        text_y = y + row_padding

        for text in cmd_lines:
            draw.text(
                (padding + row_padding, text_y),
                text,
                font=cmd_font,
                fill=(20, 20, 20)
            )
            text_y += 30 + line_gap

        text_y += 4

        for text in desc_lines:
            draw.text(
                (padding + row_padding, text_y),
                text,
                font=desc_font,
                fill=(70, 70, 70)
            )
            text_y += 28 + line_gap

        y += row_height + block_gap

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()

def get_help(module: str = "") -> str:
    help_map = load_help_map()
    module = module.strip().lower()
    lines = get_help_lines(module)

    image_bytes = render_help_image(lines)

    return MessageSegment.image(image_bytes)


@help_cmd.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    module = args.extract_plain_text().strip()

    lines = get_help_lines(module)
    image_bytes = render_help_image(lines)

    sent = await help_cmd.send(MessageSegment.image(image_bytes))
    add(event.message_id, sent["message_id"])
    return