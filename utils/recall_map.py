recall_map = {}

def add(user_msg, bot_msg):
    recall_map[str(user_msg)] = str(bot_msg)

def get(user_msg):
    return recall_map.get(str(user_msg))

def remove(user_msg):
    recall_map.pop(str(user_msg), None)