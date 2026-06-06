from nonebot import on_notice
from nonebot.adapters.onebot.v11 import Bot, GroupRecallNoticeEvent, FriendRecallNoticeEvent

from utils.recall_map import get, remove

recall_notice = on_notice(priority=1, block=False)

@recall_notice.handle()
async def _(bot: Bot, event: GroupRecallNoticeEvent | FriendRecallNoticeEvent):

    user_msg_id = event.message_id
    bot_msg_id = get(user_msg_id)

    if not bot_msg_id:
        return

    try:
        await bot.delete_msg(message_id=bot_msg_id)
        
    except:
        pass

    remove(user_msg_id)