import time
from pathlib import Path

import nonebot
from dotenv import load_dotenv
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
START_TIME = time.time()


def configure_environment() -> None:
    load_dotenv(dotenv_path=ENV_PATH)


def configure_nonebot() -> None:
    nonebot.init()

    driver = nonebot.get_driver()
    driver.register_adapter(OneBotV11Adapter)

    nonebot.load_plugin("nonebot_plugin_apscheduler")
    nonebot.load_plugins(str(BASE_DIR / "plugins"))


def main() -> None:
    configure_environment()
    configure_nonebot()
    nonebot.run()


if __name__ == "__main__":
    main()
