from django.core.management import call_command
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class HrSyncScheduler:
    """人员同步定时器"""

    def __init__(self):
        self.interval_minutes = getattr(settings, 'HR_SYNC_INTERVAL_MINUTES', 10)
        self.last_run = None

    def should_run(self):
        """检查是否应该运行同步"""
        if self.last_run is None:
            return True

        next_run = self.last_run + timedelta(minutes=self.interval_minutes)
        return timezone.now() >= next_run

    def run_sync(self):
        """执行同步"""
        try:
            logger.info("开始定时同步人员数据")
            call_command('sync_hr_persons')
            self.last_run = timezone.now()
            logger.info("定时同步人员数据完成")
        except Exception as e:
            logger.error(f"定时同步人员数据失败: {e}")


# 全局调度器实例
hr_sync_scheduler = HrSyncScheduler()


def run_hr_sync_if_needed():
    """如果需要则运行人员同步"""
    if hr_sync_scheduler.should_run():
        hr_sync_scheduler.run_sync()