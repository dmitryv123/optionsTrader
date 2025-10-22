import json
import time
import asyncio
from typing import Any, Dict
from channels.generic.websocket import AsyncWebsocketConsumer


class EchoConsumer(AsyncWebsocketConsumer):
    async def connect(self) -> None:
        await self.accept()
        await self.send_json({"ok": True, "msg": "echo connected"})

    async def receive(self, text_data: str = None, bytes_data: bytes = None) -> None:
        payload = text_data if text_data is not None else bytes_data
        await self.send(
            text_data=json.dumps({"echo": payload, "ts": time.time()})
        )

    async def send_json(self, data: Dict[str, Any]) -> None:
        await self.send(text_data=json.dumps(data))


class PnlConsumer(AsyncWebsocketConsumer):
    """
    Streams PnL ticks.
    Joins a broadcast group named 'pnl'.
    """

    group_name = "pnl"

    async def connect(self) -> None:
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"ok": True, "msg": "pnl connected"})

    async def disconnect(self, code: int) -> None:
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_json(self, data: Dict[str, Any]) -> None:
        await self.send(text_data=json.dumps(data))

    async def pnl_tick(self, event: Dict[str, Any]) -> None:
        """
        Handles messages sent with type='pnl.tick'
        """
        await self.send_json({"ts": event["ts"], "pnl": event["pnl"]})

