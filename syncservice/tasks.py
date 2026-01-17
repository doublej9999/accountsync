from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


@shared_task
def sync_hr_persons_task():
    """同步HR人员数据的定时任务"""
    try:
        logger.info("开始执行定时HR数据同步任务")
        call_command('sync_hr_persons')
        logger.info("HR数据同步任务执行完成")
        return "HR数据同步成功"
    except Exception as e:
        logger.error(f"HR数据同步任务失败: {e}")
        raise


@shared_task
def create_account_tasks_task():
    """创建账号任务的定时任务"""
    try:
        logger.info("开始执行账号任务创建定时任务")
        call_command('create_account_tasks')
        logger.info("账号任务创建定时任务执行完成")
        return "账号任务创建成功"
    except Exception as e:
        logger.error(f"账号任务创建定时任务失败: {e}")
        raise


@shared_task
def process_account_creation_tasks_task():
    """处理账号创建任务的定时任务"""
    try:
        logger.info("开始执行账号创建任务处理定时任务")
        call_command('process_account_creation_tasks')
        logger.info("账号创建任务处理定时任务执行完成")
        return "账号创建任务处理成功"
    except Exception as e:
        logger.error(f"账号创建任务处理定时任务失败: {e}")
        raise