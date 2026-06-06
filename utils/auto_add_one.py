from collections import defaultdict

from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent

from utils.recall_map import add

repeat = on_message(priority=5, block=False)

from core.config import config

ALLOW_GROUPS = config.qq.groups
BOT_ID = config.qq.bot_ids

last_msg = defaultdict(str)
last_user = defaultdict(int)
repeated = defaultdict(bool)

@repeat.handle()
async def _(event: GroupMessageEvent):
    group_id = event.group_id
    user_id = event.user_id

    msg = event.get_message()

    if not msg:
        return

    if group_id not in ALLOW_GROUPS:
        return

    if user_id in BOT_ID:
        return

    if user_id == int(event.self_id):
        return

    should_repeat = (
        last_msg[group_id] == msg
        and last_user[group_id] != user_id
        and not repeated[group_id]
    )

    if should_repeat:
        sent = await repeat.send(msg)

        add(event.message_id, sent["message_id"])

        repeated[group_id] = True

    elif last_msg[group_id] != msg:
        repeated[group_id] = False

    last_msg[group_id] = msg
    last_user[group_id] = user_id