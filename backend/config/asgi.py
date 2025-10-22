import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from realtime.routing import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})




# import os
# from django.core.asgi import get_asgi_application
# from channels.routing import ProtocolTypeRouter, URLRouter
# from django.urls import path
# from yourapp.consumers import PnlConsumer
#
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yourproj.settings')
# django_asgi = get_asgi_application()
#
# application = ProtocolTypeRouter({
#     "http": django_asgi,
#     "websocket": URLRouter([path("ws/stream/pnl/", PnlConsumer.as_asgi())]),
# })
