from nonebot.adapters.onebot.v11 import MessageSegment

from utils.recall_map import add

async def safe_send(handler, event, message):
    """
    handler: xxx.handle() 对象
    event: MessageEvent
    message: str / Message
    """

    sent = await handler.send(message)

    add(
        event.message_id,
        sent["message_id"]
    )

    return sent