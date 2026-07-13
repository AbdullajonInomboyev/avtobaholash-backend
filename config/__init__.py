# Celery app'ni Django ishga tushganda import qilamiz — shunda @shared_task
# vazifalari to'g'ri (sozlangan) app'ga bog'lanadi. Dev'da EAGER, prod'da Redis.
from .celery import app as celery_app

__all__ = ("celery_app",)