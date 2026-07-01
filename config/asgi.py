"""
ASGI konfiguratsiyasi — WebSocket (imtihon real-time monitoring)
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from apps.submissions import routing as submission_routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(
            submission_routing.websocket_urlpatterns
        )
    ),
})
