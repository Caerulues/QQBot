from pathlib import Path
import tomllib
from dataclasses import dataclass


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.toml"


@dataclass
class ServerConfig:
    path: str
    command: str
    terminal_title: str
    launch_mode: str = "auto"


@dataclass
class RconConfig:
    host: str
    port: int
    password: str


@dataclass
class MinecraftConfig:
    port: int
    name: str
    status_address: str
    log_path: str
    ping_target: str = "test6.ustc.edu.cn"


@dataclass
class QQConfig:
    admin_users: set[int]
    groups: set[int]
    bridge_group_id: int | None
    event_group_id: int | None
    bot_ids: set[int]
    ping_user_id: int | None = None


@dataclass
class BotConfig:
    server: ServerConfig
    rcon: RconConfig
    minecraft: MinecraftConfig
    qq: QQConfig
    data_dir: str = "data"


def load_config() -> BotConfig:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "缺少 config.toml。请复制 config.example.toml 为 config.toml，并填写本机配置。"
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