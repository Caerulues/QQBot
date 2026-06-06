import nonebot
import time

from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent, GroupRecallNoticeEvent

from dotenv import load_dotenv
from pathlib import Path

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

nonebot.load_plugin("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

nonebot.load_plugins("core")
nonebot.load_plugins("utils")
nonebot.load_plugins("plugins")
nonebot.load_plugins("mcserver")

START_TIME = time.time()

if __name__ == "__main__":
    nonebot.run()