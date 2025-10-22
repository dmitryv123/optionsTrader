from django.urls import path
from .consumers import PnlConsumer, EchoConsumer

websocket_urlpatterns = [
    path("ws/stream/pnl/", PnlConsumer.as_asgi()),
    path("ws/echo/", EchoConsumer.as_asgi()),  # handy for quick connectivity tests
]
