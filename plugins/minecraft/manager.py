from __future__ import annotations
import asyncio, inspect, logging
from dataclasses import dataclass
from typing import Any, Callable, Awaitable
import websockets
from websockets.asyncio.server import ServerConnection
from .config import BotConfig
from .protocol import enc, dec, request, command

log = logging.getLogger("mc_bridge")


@dataclass(slots=True)
class Node:
    server_id: str
    server_name: str
    ws: ServerConnection


class BridgeManager:
    def __init__(self, cfg: BotConfig):
        self.cfg = cfg
        self.nodes = {}
        self.handlers = []
        self.pending = {}
        self.lock = asyncio.Lock()

    def add_handler(self, h):
        self.handlers.append(h)

    def list_servers(self):
        return [
            {"server_id": n.server_id, "server_name": n.server_name}
            for n in sorted(self.nodes.values(), key=lambda x: x.server_id)
        ]

    async def _emit(self, msg):
        for h in tuple(self.handlers):
            try:
                r = h(msg)
                if inspect.isawaitable(r):
                    await r
            except Exception:
                log.exception("event handler failed")

    async def send_chat(self, server_ids: list[str], name: str, text: str):
        payload = enc(command("chat", {"name": name, "message": text}))
        targets = self._targets(server_ids)
        await asyncio.gather(
            *(n.ws.send(payload) for n in targets), return_exceptions=True
        )

    def _targets(self, ids):
        if "*" in ids or "all" in ids:
            return list(self.nodes.values())
        return [self.nodes[x] for x in ids if x in self.nodes]

    async def call(self, server_id, action, data=None, timeout=15):
        n = self.nodes.get(server_id)
        if not n:
            raise KeyError(server_id)
        p = request(action, data)
        fut = asyncio.get_running_loop().create_future()
        self.pending[p["request_id"]] = fut
        try:
            await n.ws.send(enc(p))
            return await asyncio.wait_for(fut, timeout)
        finally:
            self.pending.pop(p["request_id"], None)

    async def _register(self, ws, msg):
        if msg.get("token") != self.cfg.token:
            await ws.close(4001, "unauthorized")
            raise PermissionError
        sid = str(msg.get("server_id", "")).strip()
        name = str(msg.get("server_name", "")).strip() or self.cfg.server_name_map.get(
            sid, sid
        )
        if not sid:
            raise ValueError("server_id required")
        node = Node(sid, name, ws)
        async with self.lock:
            old = self.nodes.get(sid)
            if old and old.ws is not ws:
                await old.ws.close(4002, "replaced")
            self.nodes[sid] = node
        await ws.send(
            enc({"type": "register_ok", "server_id": sid, "server_name": name})
        )
        await self._emit(
            {
                "type": "connection",
                "state": "online",
                "server_id": sid,
                "server_name": name,
            }
        )
        return node

    async def _handler(self, ws):
        node = None
        try:
            first = dec(await asyncio.wait_for(ws.recv(), 10))
            if first.get("type") != "register":
                raise ValueError("register first")
            node = await self._register(ws, first)
            async for raw in ws:
                msg = dec(raw)
                typ = msg.get("type")
                if typ == "event":
                    msg["server_id"] = node.server_id
                    msg["server_name"] = node.server_name
                    await self._emit(msg)
                elif typ == "response":
                    fut = self.pending.get(str(msg.get("request_id")))
                    if fut and not fut.done():
                        fut.set_result(msg)
        except websockets.ConnectionClosed:
            pass
        except PermissionError:
            log.warning("unauthorized agent")
        except Exception:
            log.exception("agent protocol error")
        finally:
            if node:
                async with self.lock:
                    if self.nodes.get(node.server_id) is node:
                        self.nodes.pop(node.server_id, None)
                await self._emit(
                    {
                        "type": "connection",
                        "state": "offline",
                        "server_id": node.server_id,
                        "server_name": node.server_name,
                    }
                )

    async def serve_forever(self):
        async with websockets.serve(
            self._handler,
            self.cfg.host,
            self.cfg.port,
            ping_interval=20,
            ping_timeout=20,
            max_size=2**20,
        ):
            log.info("listening ws://%s:%s", self.cfg.host, self.cfg.port)
            await asyncio.Future()
