"""
WSGI konfiguratsiyasi
Daphne ASGI ishlatilsa ham, ba'zi toollar WSGI talab qilishi mumkin.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

application = get_wsgi_application()
