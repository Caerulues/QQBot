from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class BotConfig:
    host: str = "127.0.0.1"
    port: int = 3001
    token: str = ""
    command_start: str = "."
    bridge_groups: dict[int, list[str]] = field(default_factory=dict)
    event_groups: dict[int, list[str]] = field(default_factory=dict)
    admin_users: set[int] = field(default_factory=set)
    forward_commands: bool = False
    server_name_map: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        token = str(raw.get("token", ""))
        if not token or token == "change-this-token":
            raise ValueError("请修改 Bot token")
        cv = lambda x: {int(k): list(v) for k, v in x.items()}
        return cls(
            str(raw.get("host", "127.0.0.1")),
            int(raw.get("port", 3001)),
            token,
            str(raw.get("command_start", ".")),
            cv(raw.get("bridge_groups", {})),
            cv(raw.get("event_groups", {})),
            {int(x) for x in raw.get("admin_users", [])},
            bool(raw.get("forward_commands", False)),
            dict(raw.get("server_name_map", {})),
        )
