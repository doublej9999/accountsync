import os
from celery import Celery

# 设置Django的默认设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountsync.settings')

app = Celery('accountsync')

# 从Django设置中加载配置，命名空间为CELERY
app.config_from_object('django.conf:settings', namespace='CELERY')

# 明确设置时区
app.conf.timezone = 'Asia/Shanghai'

# 自动发现任务
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')