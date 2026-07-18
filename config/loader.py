import os
from pathlib import Path
import tomllib

from .models import (
    BotConfig,
    MinecraftConfig,
    QQConfig,
    RconConfig,
    ServerConfig,
)


BASE_DIR = Path(__file__).resolve().parent.parent


def resolve_config_path() -> Path:
    configured_path = os.getenv("QQBOT_CONFIG")
    if configured_path:
        path = Path(configured_path).expanduser()
        return path if path.is_absolute() else BASE_DIR / path

    local_path = BASE_DIR / "config.local.toml"
    if local_path.exists():
        return local_path

    return BASE_DIR / "config.toml"


CONFIG_PATH = resolve_config_path()


def load_config() -> BotConfig:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "缺少配置文件。请复制 config.example.toml 为 config.local.toml，并填写本机配置。"
        )

    with open(CONFIG_PATH, "rb") as f:
        raw = tomllib.load(f)

    server = raw.get("server", {})
    rcon = raw.get("rcon", {})
    minecraft = raw.get("minecraft", {})
    qq = raw.get("qq", {})

    server_path = server.get("path", "")
    mc_port = int(minecraft.get("port", 25565))

    return BotConfig(
        server=ServerConfig(
            path=server_path,
            command=server.get("command", ""),
            terminal_title=server.get("terminal_title", "MINECRAFT_SERVER_TERMINAL"),
            launch_mode=server.get("launch_mode", "auto"),
        ),
        rcon=RconConfig(
            host=rcon.get("host", "127.0.0.1"),
            port=int(rcon.get("port", 25575)),
            password=rcon.get("password", ""),
        ),
        minecraft=MinecraftConfig(
            port=mc_port,
            name=minecraft.get("name", "Minecraft Server"),
            status_address=minecraft.get("status_address", f"127.0.0.1:{mc_port}"),
            log_path=minecraft.get("log_path", str(Path(server_path) / "logs/latest.log")),
            ping_target=minecraft.get("ping_target", "test6.ustc.edu.cn"),
            bot_ids=set(minecraft.get("bot_ids", [])),
            ignore_player_ids=set(minecraft.get("ignore_player_ids", [])),
            translate_message=minecraft.get("translate_message", False),
            enable_ipv6_monitor=minecraft.get("enable_ipv6_monitor", True),
        ),
        qq=QQConfig(
            admin_users=set(qq.get("admin_users", [])),
            groups=set(qq.get("groups", [])),
            bridge_group_id=qq.get("bridge_group_id"),
            event_group_id=qq.get("event_group_id"),
            bot_ids=set(qq.get("bot_ids", [])),
            ping_user_id=qq.get("ping_user_id"),
        ),
        data_dir=str(BASE_DIR / raw.get("data_dir", "data")),
    )

config = load_config()