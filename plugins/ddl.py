import uuid
import json
import jionlp as jio

from PIL import Image, ImageDraw
import io
import textwrap

from pathlib import Path
from datetime import datetime

from nonebot import on_command, require, get_bot
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment,
    MessageEvent
)

from utils.recall_map import add

require("nonebot_plugin_apscheduler")

from nonebot_plugin_apscheduler import scheduler

from plugins.help import get_help
from core.json_store import (
    load_data,
    save_data
)
from core.config import config
from core.font import load_font
from core.command import get_cmd_start
from core.parser import split_by_bar

cmd_start = get_cmd_start()

DDL_PATH = Path(config.data_dir) / "deadlines"
DDL_PATH.mkdir(parents=True, exist_ok=True)

ddl_cmd = on_command("ddl", priority=5, block=True)

# MARK: 提醒规则（动态）

REMIND_STAGES = [
    (0, "remind_now", "now"),
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
        print(f"[Parse Error] {e}")
        return None

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
async def _(event, state: T_State):
    raw_msg = str(event.get_message()).strip()

    args = raw_msg.split()

    if len(args) < 2:
        sent = ddl_cmd.send(get_help("ddl"))
        add(event.message_id, sent["message_id"])
        return

    action = args[1]

    user_id = event.user_id
    data = load_data(DDL_PATH, user_id)

    # MARK: add

    if action == "add":
        add_msg = raw_msg.replace(f"{cmd_start}ddl add", "").strip()
        add_args = add_msg.split()

        if len(add_args) < 2:
            return

        lines = [
            x.strip()
            for x in add_msg.split("\n")
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

        save_data(DDL_PATH, user_id, data)

        if not added:
            sent = await ddl_cmd.send("无法解析时间")

        else:
            sent = await ddl_cmd.send("已添加DDL:\n" + "\n".join(added))

        add(event.message_id, sent["message_id"])
        return

    # MARK: mv

    elif action == "mv":
        mv_msg = raw_msg.replace(f"{cmd_start}ddl mv", "", 1).strip()
        mv_args = mv_msg.split()

        if len(mv_args) < 1:
            sent = await ddl_cmd.send("请输入执行操作")
            add(event.message_id, sent["message_id"])
            return

        mv_action = mv_args[0]

        if mv_action == "-n":
            content = raw_msg.replace(f"{cmd_start}ddl mv -n", "", 1).strip()
            old_title, new_title = split_by_bar(content)

            if not old_title or not new_title:
                sent = await ddl_cmd.send(
                    f"格式：{cmd_start}ddl mv -n <原任务名称> | <新任务名称>"
                )
                add(event.message_id, sent["message_id"])
                return

            matches = [
                item for item in data
                if old_title in item["title"]
            ]

            if not matches:
                sent = await ddl_cmd.send("未找到任务")
                add(event.message_id, sent["message_id"])
                return

            if len(matches) == 1:
                matches[0]["title"] = new_title
                save_data(DDL_PATH, user_id, data)

                sent = await ddl_cmd.send(f"已修改任务名称：{new_title}")
                add(event.message_id, sent["message_id"])
                return

            state["pending_action"] = "mv_name"
            state["candidates"] = matches
            state["user_id"] = user_id
            state["new_title"] = new_title

            msg = "找到多个匹配项，请回复编号选择要修改哪一项：\n"
            msg += "\n".join(
                f"{i + 1}. {item['title']}"
                for i, item in enumerate(matches)
            )

            await ddl_cmd.send(msg)
            await ddl_cmd.pause()


        elif mv_action == "-t":
            content = raw_msg.replace(f"{cmd_start}ddl mv -t", "", 1).strip()
            title, time_str = split_by_bar(content)

            if not title or not time_str:
                sent = await ddl_cmd.send(
                    f"格式：{cmd_start}ddl mv -t <任务名称> | <新DDL>"
                )
                add(event.message_id, sent["message_id"])
                return

            parsed = parse_ddl_line(f"{title} {time_str}")

            if not parsed:
                sent = await ddl_cmd.send("无法解析时间")
                add(event.message_id, sent["message_id"])
                return

            matches = [
                item for item in data
                if title in item["title"]
            ]

            if not matches:
                sent = await ddl_cmd.send("未找到任务")
                add(event.message_id, sent["message_id"])
                return

            new_time = parsed["time"].timestamp()

            if len(matches) == 1:
                matches[0]["time"] = new_time
                matches[0]["reminded_1w"] = False
                matches[0]["reminded_1d"] = False
                matches[0]["reminded_1h"] = False

                save_data(DDL_PATH, user_id, data)

                sent = await ddl_cmd.send("已修改DDL时间")
                add(event.message_id, sent["message_id"])
                return

            state["pending_action"] = "mv_time"
            state["candidates"] = matches
            state["user_id"] = user_id
            state["new_time"] = new_time

            msg = "找到多个匹配项，请回复编号选择要修改哪一项：\n"
            msg += "\n".join(
                f"{i + 1}. {item['title']}"
                for i, item in enumerate(matches)
            )

            await ddl_cmd.send(msg)
            await ddl_cmd.pause()

    # MARK: list

    elif action == "list":
        now = datetime.now().timestamp()

        valid_data = [
            x for x in data
            if x["time"] > now
        ]

        if not valid_data:
            sent = await ddl_cmd.send("你的DDL已经清空，可以休息一会了～")
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
        keyword = raw_msg.replace(f"{cmd_start}ddl del", "", 1).strip()

        if not keyword:
            sent = await ddl_cmd.send("请输入要删除的任务名称")
            add(event.message_id, sent["message_id"])
            return

        matches = [
            item for item in data
            if keyword in item["title"]
        ]

        if not matches:
            sent = await ddl_cmd.send(f"未找到与 {keyword} 相关的DDL")
            add(event.message_id, sent["message_id"])
            return

        if len(matches) == 1:
            data.remove(matches[0])
            save_data(DDL_PATH, user_id, data)
            sent = await ddl_cmd.send(f"已删除: {matches[0]['title']}")
            add(event.message_id, sent["message_id"])
            return

        if len(matches) == 1:
            data.remove(matches[0])
            save_data(DDL_PATH, user_id, data)
            sent = await ddl_cmd.send(f"已删除: {matches[0]['title']}")
            add(event.message_id, sent["message_id"])

        state["pending_action"] = "delete"
        state["candidates"] = matches
        state["user_id"] = user_id

        msg = "找到多个匹配项，请回复编号选择需要删除的项目：\n"
        msg += "\n".join(
            f"{i + 1}. {item['title']}"
            for i, item in enumerate(matches)
        )

        await ddl_cmd.send(msg)
        await ddl_cmd.pause()

    # MARK: help

    elif action == "help":
        sent = await ddl_cmd.send(get_help("ddl"))
        add(event.message_id, sent["message_id"])


    else:
        sent = await ddl_cmd.send("未知操作")
        add(event.message_id, sent["message_id"])

@ddl_cmd.receive()
async def _(event: MessageEvent, state: T_State):
    if "pending_action" not in state:
        return

    choice = str(event.get_message()).strip()

    if not choice.isdigit():
        await ddl_cmd.reject("请输入数字编号，例如：1")

    action = state["pending_action"]
    matches = state["candidates"]
    user_id = state["user_id"]

    index = int(choice) - 1

    if index < 0 or index >= len(matches):
        await ddl_cmd.reject("编号不存在，请重新输入")

    target = matches[index]
    data = load_data(DDL_PATH, user_id)

    for item in data:
        if item["id"] != target["id"]:
            continue

        if action == "delete":
            data.remove(item)
            save_data(DDL_PATH, user_id, data)
            await ddl_cmd.finish(f"已删除：{item['title']}")

        elif action == "mv_name":
            item["title"] = state["new_title"]
            save_data(DDL_PATH, user_id, data)
            await ddl_cmd.finish(f"已修改任务名称：{item['title']}")

        elif action == "mv_time":
            item["time"] = state["new_time"]
            item["reminded_1w"] = False
            item["reminded_1d"] = False
            item["reminded_1h"] = False

            save_data(DDL_PATH, user_id, data)
            await ddl_cmd.finish(f"已修改DDL时间：{item['title']}")

    await ddl_cmd.finish("任务不存在，可能已被修改或删除")

# MARK: 定时提醒

@scheduler.scheduled_job("interval", minutes=1)
async def ddl_reminder():
    try:
        bot = get_bot()

    except:
        return

    now = datetime.now().timestamp()

    for file in DDL_PATH.glob("*.json"):
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

                    elif remind_type == "now":
                        msg += " 已经截止"

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