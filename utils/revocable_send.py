from utils.recall_map import add

async def revocable_send(handler, event, message):
    sent = await handler.send(message)
    add(
        event.message_id,
        sent["message_id"]
    )
    return sent