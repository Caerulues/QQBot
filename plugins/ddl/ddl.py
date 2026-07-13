import uuid
import json
import re

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

from plugins.common.help import get_help
from storage.json_storage import (
    load_data,
    save_data
)
from config import config
from utils.command import get_cmd_start
from utils.parser import split_by_bar
from utils.choice_prompt import (
    ask_choice,
    parse_choice,
    clear_choice_state,
    format_ddl_candidate,
)
from .remind_level_checker import (
    should_remind,
    mark_current_and_wider_stages,
)
from .time_parser import parse_ddl_line
from .build_ddl_image import build_ddl_image

cmd_start = get_cmd_start()

DDL_PATH = Path(config.data_dir) / "ddl"
DDL_PATH.mkdir(parents=True, exist_ok=True)

ddl_cmd = on_command("ddl", priority=5, block=True)

# MARK: 命令处理

@ddl_cmd.handle()
async def _(event: MessageEvent, state: T_State):
    if "pending_action" in state:
        return

    raw_msg = str(event.get_message()).strip()
    args = raw_msg.split()

    if len(args) < 2:
        sent = await ddl_cmd.send(get_help("ddl"))
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

        if mv_action == "-rn" or mv_action == "rename":
            content = re.sub(
                rf"^{re.escape(cmd_start)}ddl\s+mv\s+(?:-rn|--rename)\s*",
                "",
                raw_msg,
                count=1
            ).strip()
            old_title, new_title = split_by_bar(content)

            if not old_title or not new_title:
                sent = await ddl_cmd.send(
                    f"格式：{cmd_start}ddl mv -rn <原任务名称> | <新任务名称>"
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

            await ask_choice(
                ddl_cmd,
                state,
                action="move_rename",
                candidates=matches,
                user_id=user_id,
                payload={"new_title": new_title},
                title="找到多个匹配项，请回复编号选择要修改哪一项",
                formatter=format_ddl_candidate,
            )
            return


        elif mv_action == "-rs" or mv_action == "--reschedule":
            content = re.sub(
                rf"^{re.escape(cmd_start)}ddl\s+mv\s+(?:-rn|--reschedule)\s*",
                "",
                raw_msg,
                count=1
            ).strip()
            title, time_str = split_by_bar(content)

            if not title or not time_str:
                sent = await ddl_cmd.send(
                    f"格式：{cmd_start}ddl mv -rs <任务名称> | <新DDL>"
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

            await ask_choice(
                ddl_cmd,
                state,
                action="move_reschedule",
                candidates=matches,
                user_id=user_id,
                payload={"new_time": new_time},
                title="找到多个匹配项，请回复编号选择要修改哪一项",
                formatter=format_ddl_candidate,
            )
            return

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
            title = matches[0]["title"]
            data.remove(matches[0])
            save_data(DDL_PATH, user_id, data)
            sent = await ddl_cmd.send(f"已删除: {title}")
            add(event.message_id, sent["message_id"])
            return

        await ask_choice(
            ddl_cmd,
            state,
            action="delete",
            candidates=matches,
            user_id=user_id,
            title="找到多个匹配项，请回复编号选择需要删除的项目",
            formatter=format_ddl_candidate,
        )
        return

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

    action = state["pending_action"]
    user_id = state["user_id"]
    payload = state.get("payload", {})

    _, target = await parse_choice(ddl_cmd, event, state)

    target_id = target.get("id")

    if not target_id:
        clear_choice_state(state)
        await ddl_cmd.finish("任务不存在 id，可能已被修改或删除")

    data = load_data(DDL_PATH, user_id)

    target_index = None
    target_item = None

    for i, item in enumerate(data):
        if item.get("id") == target_id:
            target_index = i
            target_item = item
            break

    if target_index is None or target_item is None:
        clear_choice_state(state)
        await ddl_cmd.finish("任务不存在，可能已被修改或删除")

    if action == "delete":
        title = target_item["title"]

        del data[target_index]
        save_data(DDL_PATH, user_id, data)

        clear_choice_state(state)
        await ddl_cmd.finish(f"已删除：{title}")

    elif action == "move_rename":
        new_title = payload.get("new_title")

        if not new_title:
            clear_choice_state(state)
            await ddl_cmd.finish("缺少新任务名称，请重新执行命令")

        target_item["title"] = new_title
        save_data(DDL_PATH, user_id, data)

        clear_choice_state(state)
        await ddl_cmd.finish(f"已修改任务名称：{target_item['title']}")

    elif action == "move_reschedule":
        new_time = payload.get("new_time")

        if not new_time:
            clear_choice_state(state)
            await ddl_cmd.finish("缺少新 DDL 时间，请重新执行命令")

        target_item["time"] = new_time
        target_item["reminded_1w"] = False
        target_item["reminded_1d"] = False
        target_item["reminded_1h"] = False

        save_data(DDL_PATH, user_id, data)

        clear_choice_state(state)
        await ddl_cmd.finish(f"已修改 DDL 时间：{target_item['title']}")

    clear_choice_state(state)
    await ddl_cmd.finish("未知操作")

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