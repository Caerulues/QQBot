from dataclasses import dataclass

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
    bot_ids: set[str]
    ignore_player_ids: set[str]
    translate_message: bool
    enable_ipv6_monitor: bool
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
