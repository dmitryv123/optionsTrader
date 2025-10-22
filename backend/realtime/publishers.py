"""
Helpers your jobs/views can call to push events into WS groups.
Use async_to_sync for sync contexts (management commands, views, celery tasks).
"""
import time
from typing import Optional
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def publish_pnl(pnl_value: float, *, group: str = "pnl", ts_ms: Optional[int] = None) -> None:
    """
    Publish one PnL tick to the 'pnl' group.
    In multi-account scenarios, call with group=f"pnl:{account_id}".
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    ts = ts_ms if ts_ms is not None else int(time.time() * 1000)
    async_to_sync(channel_layer.group_send)(
        group,
        {"type": "pnl.tick", "ts": ts, "pnl": float(pnl_value)},
    )
