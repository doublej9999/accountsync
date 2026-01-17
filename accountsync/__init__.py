# 这将确保在Django应用启动时加载Celery
from .celery import app as celery_app

__all__ = ('celery_app',)