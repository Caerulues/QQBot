import json
from pathlib import Path

from nonebot import get_bot, logger, require

from core.ipv6 import get_ipv6

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler


from core.config import config

GROUP_IDS = config.qq.groups
IP_FILE_PATH = Path(config.data_dir) / "ip"
IP_FILE_PATH.mkdir(parents=True, exist_ok=True)

JOB_ID = "minecraft_ipv6_monitor"

server_running = False


def get_ip_file():
    return IP_FILE_PATH / "ipv6.json"


def load_ip() -> str:
    file = get_ip_file()

    if not file.exists():
        return ""

    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("ipv6", "")
    except Exception as e:
        logger.warning(f"读取IPv6记录失败: {e}")
        return ""


def save_ip(ipv6: str):
    file = get_ip_file()

    with open(file, "w", encoding="utf-8") as f:
        json.dump(
            {"ipv6": ipv6},
            f,
            ensure_ascii=False,
            indent=2
        )


async def send_ipv6_to_groups(ipv6: str, reason: str):
    bot = get_bot()

    message = (
        f"服务器IPv6地址{reason}\n"
        f"[{ipv6}]:{config.minecraft.port}"
    )

    for group_id in GROUP_IDS:
        try:
            await bot.send_group_msg(
                group_id=group_id,
                message=message
            )
        except Exception as e:
            logger.warning(f"IPv6消息发送到群 {group_id} 失败: {e}")


async def check_ipv6(force_send: bool = False):
    if not server_running:
        logger.info("Minecraft服务端未由Bot标记为运行，跳过IPv6检查")
        return

    ipv6 = get_ipv6()

    if not ipv6:
        logger.warning("未获取到有效IPv6")
        return

    if ipv6.startswith("获取失败"):
        logger.warning(f"IPv6获取失败: {ipv6}")
        return

    last_ipv6 = load_ip()

    if force_send:
        save_ip(ipv6)
        await send_ipv6_to_groups(ipv6, "如下")
        return

    if not last_ipv6:
        save_ip(ipv6)
        await send_ipv6_to_groups(ipv6, "已记录")
        return

    if ipv6 == last_ipv6:
        return

    save_ip(ipv6)
    await send_ipv6_to_groups(ipv6, "已更新")


async def start_ipv6_monitor():
    global server_running

    server_running = True

    await check_ipv6(force_send=True)

    if scheduler.get_job(JOB_ID):
        return

    scheduler.add_job(
        check_ipv6,
        "interval",
        minutes=10,
        id=JOB_ID,
        kwargs={"force_send": False},
        replace_existing=True,
    )

    logger.info("Minecraft IPv6 monitor 已启动")


def stop_ipv6_monitor():
    global server_running

    server_running = False

    job = scheduler.get_job(JOB_ID)

    if not job:
        return

    scheduler.remove_job(JOB_ID)
    logger.info("Minecraft IPv6 monitor 已停止")