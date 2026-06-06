from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageEvent

from utils.recall_map import add

HELP_MAP = {
    "ddl": (
        "当前指令: .ddl\n"
        "\n"
        "子命令列表\n"
        ".ddl add <任务名称> <截止时间>\n"
        ".ddl list\n"
        ".ddl del <UUID>"
    ),
    
    "": (
        "Cauxium帮助信息\n"
        "指令列表\n"
        ".ddl - 任务截止日期功能模块\n"
        ".echo - 测试是否在线\n"
        ".ipv6 - 显示当前IPv6地址\n"
        ".ping - 测试当前网络及消息处理延迟\n"
        ".status - 显示当前系统状态\n"
    )
}

def get_help(module: str) -> str:
    return HELP_MAP.get(module, "未找到该指令的帮助信息")

help_cmd = on_command("help", priority=5, block=True)

@help_cmd.handle()
async def _(event: MessageEvent):
    args = event.get_plaintext().replace(".help", "").strip()

    sent = await help_cmd.send(get_help(args))
    add(event.message_id, sent["message_id"])
    return