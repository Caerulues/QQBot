import json
import uuid
import jionlp as jio

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

DATA_PATH = Path(config.data_dir) / "deadlines"
DATA_PATH.mkdir(parents=True, exist_ok=True)

ddl_cmd = on_command("ddl", priority=5, block=True)

# MARK: 数据存储

def get_user_file(user_id: int):
    return DATA_PATH / f"{user_id}.json"

def load_data(user_id: int):
    file = get_user_file(user_id)

    if not file.exists():
        with open(file, "w", encoding="utf-8") as f:
            json.dump([], f)

        return []

    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(user_id: int, data):
    file = get_user_file(user_id)

    with open(file, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

# MARK: 提醒规则（动态）

REMIND_STAGES = [
    (3600, "reminded_1h", "1h"),
    (86400, "reminded_1d", "1d"),
    (7 * 86400, "reminded_1w", "1w"),
]

def should_remind(item, remain):
    if remain <= 0:
        return None

    for index, (threshold, flag, tag) in enumerate(REMIND_STAGES):
        if remain <= threshold:
            if item.get(flag, False):
                return None

            return index, tag

    return None

def mark_current_and_wider_stages(item, current_index: int):
    """
    当前阶段触发后，把当前阶段以及更宽松阶段都标记为已提醒。

    例如：
    触发 1d，则同时标记 1d 和 1w。
    触发 1h，则同时标记 1h、1d、1w。
    """
    for _, flag, _ in REMIND_STAGES[current_index:]:
        item[flag] = True

# MARK: 时间处理

def parse_ddl_line(text: str):
    try:
        parts = text.rsplit(" ", 1)

        if len(parts) != 2:
            return None

        title = parts[0].strip()
        time_str = parts[1].strip()

        result = jio.parse_time(
            time_str,
            time_base=datetime.now()
        )

        if not result:
            return None

        start_time = result["time"][0]

        if isinstance(start_time, datetime):
            ddl_time = start_time

        else:
            ddl_time = datetime.strptime(
                start_time,
                "%Y-%m-%d %H:%M:%S"
            )

        return {
            "title": title,
            "time": ddl_time
        }

    except Exception as e:
        print(f"[DDL Parse Error] {e}")
        return None

# MARK: 字体

def load_font(size):
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/STHeiti Medium.ttc",
    ]

    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue

    raise RuntimeError("No valid CJK font found")

# MARK: 图片生成

def build_ddl_image(data):
    width = 1000
    padding = 40
    row_h = 70

    base_font_size = 32

    if len(data) > 10:
        base_font_size = 24

    if len(data) > 20:
        base_font_size = 16

    font = load_font(base_font_size)

    height = padding * 2 + 80 + len(data) * row_h

    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    y = padding

    # 表头
    draw.text((padding + 10, y + 8), "UUID", font=font, fill=(0, 0, 0))
    draw.text((padding + 200, y + 8), "TITLE", font=font, fill=(0, 0, 0))
    draw.text((padding + 550, y + 8), "DEADLINE", font=font, fill=(0, 0, 0))
    draw.text((padding + 800, y + 8), "REMAIN", font=font, fill=(0, 0, 0))

    y += 50

    for item in data:
        remain = int(item["time"] - datetime.now().timestamp())

        if remain < 0:
            color = (255, 80, 80)

        elif remain < 86400:
            color = (255, 180, 0)

        else:
            color = (0, 0, 0)

        if remain < 0:
            remain_text = "EXPIRED"

        else:
            days = remain // 86400
            hours = (remain % 86400) // 3600
            minutes = (remain % 3600) // 60

            if days > 0:
                remain_text = f"{days}d {hours}h"

            else:
                remain_text = f"{hours}h {minutes}m"

        dt = datetime.fromtimestamp(
            item["time"]
        ).strftime("%m-%d %H:%M")

        draw.text(
            (padding + 10, y),
            item["id"],
            font=font,
            fill=color
        )

        title_lines = textwrap.wrap(
            item["title"],
            width=12
        )

        for i, line in enumerate(title_lines[:2]):
            draw.text(
                (padding + 200, y + i * 26),
                line,
                font=font,
                fill=color
            )

        draw.text(
            (padding + 550, y),
            dt,
            font=font,
            fill=color
        )

        draw.text(
            (padding + 800, y),
            remain_text,
            font=font,
            fill=color
        )

        y += row_h

    buf = io.BytesIO()
    img.save(buf, format="PNG")

    return buf.getvalue()

# MARK: 命令处理

@ddl_cmd.handle()
async def _(event):
    raw_msg = str(event.get_message()).strip()

    args = raw_msg.split()

    if len(args) < 2:
        sent = await ddl_cmd.send(get_help("ddl"))
        add(event.message_id, sent["message_id"])
        return

    action = args[1]

    user_id = event.user_id
    data = load_data(user_id)

    # MARK: add

    if action == "add":
        raw = raw_msg.replace(".ddl add", "").strip()

        lines = [
            x.strip()
            for x in raw.split("\n")
            if x.strip()
        ]

        if not lines:
            sent = await ddl_cmd.send("请输入任务名称和截止时间")
            add(event.message_id, sent["message_id"])
            return

        added = []

        for line in lines:
            parsed = parse_ddl_line(line)

            if not parsed:
                continue

            title = parsed["title"]
            ddl_time = parsed["time"]

            item = {
                "id": str(uuid.uuid4())[:8],
                "title": title,
                "time": ddl_time.timestamp(),

                "reminded_1w": False,
                "reminded_1d": False,
                "reminded_1h": False
            }

            if isinstance(event, GroupMessageEvent):
                item["group_id"] = event.group_id

            data.append(item)
            added.append(title)

        save_data(user_id, data)

        if not added:
            sent = await ddl_cmd.send("无法解析时间")

        else:
            sent = await ddl_cmd.send(
                "已添加DDL:\n" + "\n".join(added)
            )

        add(event.message_id, sent["message_id"])
        return

    # MARK: list

    elif action == "list":
        now = datetime.now().timestamp()

        valid_data = [
            x for x in data
            if x["time"] > now
        ]

        if not valid_data:
            sent = await ddl_cmd.send(
                "你的DDL已经清空，可以休息一会了～"
            )

            add(event.message_id, sent["message_id"])
            return

        valid_data.sort(key=lambda x: x["time"])

        img = build_ddl_image(valid_data)

        sent = await ddl_cmd.send(
            MessageSegment.image(img)
        )

        add(event.message_id, sent["message_id"])
        return

    # MARK: del

    elif action == "del":
        if len(args) < 3:
            sent = await ddl_cmd.send("请输入ID")
            add(event.message_id, sent["message_id"])
            return

        ddl_id = args[2]

        new_data = [
            x for x in data
            if x["id"] != ddl_id
        ]

        if len(new_data) == len(data):
            sent = await ddl_cmd.send("未找到对应DDL")
            add(event.message_id, sent["message_id"])
            return

        save_data(user_id, new_data)

        sent = await ddl_cmd.send("已删除")
        add(event.message_id, sent["message_id"])
        return

    # MARK: help

    elif action == "help":
        sent = await ddl_cmd.send(get_help("ddl"))
        add(event.message_id, sent["message_id"])
        return

    else:
        sent = await ddl_cmd.send("未知操作")
        add(event.message_id, sent["message_id"])
        return

# MARK: 定时提醒

@scheduler.scheduled_job("interval", minutes=1)
async def ddl_reminder():
    try:
        bot = get_bot()

    except:
        return

    now = datetime.now().timestamp()

    for file in DATA_PATH.glob("*.json"):
        try:
            user_id = int(file.stem)

        except:
            continue

        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

        except Exception as e:
            print(f"Failed to load {file}: {e}")
            continue

        changed = False
        new_data = []

        for item in data:
            remain = item["time"] - now

            # 超过一分钟自动删除
            if remain <= -60:
                changed = True
                continue

            remind_result = should_remind(item, remain)

            if remind_result:
                try:
                    current_index, remind_type = remind_result

                    msg = f"{item['title']}"

                    if remind_type == "1w":
                        msg += " 将于一周内截止"

                    elif remind_type == "1d":
                        msg += " 将于一天内截止"

                    elif remind_type == "1h":
                        msg += " 将于一小时内截止"

                    mark_current_and_wider_stages(item, current_index)

                    if item.get("group_id"):
                        await bot.send_private_msg(
                            user_id=user_id,
                            group_id=item["group_id"],
                            message=msg
                        )

                    else:
                        await bot.send_private_msg(
                            user_id=user_id,
                            message=msg
                        )

                    changed = True

                except Exception as e:
                    print(
                        f"Failed to send reminder to {user_id}: {e}"
                    )

            new_data.append(item)

        if changed:
            try:
                with open(file, "w", encoding="utf-8") as f:
                    json.dump(
                        new_data,
                        f,
                        ensure_ascii=False,
                        indent=2
                    )

            except Exception as e:
                print(f"Failed to save {file}: {e}")