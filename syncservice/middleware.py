from django.utils.deprecation import MiddlewareMixin

from syncservice.cron.scheduler import run_hr_sync_if_needed, run_task_creation_if_needed, \
    run_account_creation_if_needed


class HrSyncMiddleware(MiddlewareMixin):
    """人员同步中间件 - 在请求中检查是否需要运行定时任务"""

    def __init__(self, get_response=None):
        super().__init__(get_response)

    def process_request(self, request):
        # 只在非静态文件请求时检查
        if not request.path.startswith('/static/') and not request.path.startswith('/media/'):
            try:
                # 独立运行三个定时任务
                run_hr_sync_if_needed()
                run_task_creation_if_needed()
                run_account_creation_if_needed()
            except Exception as e:
                # 不让同步错误影响正常请求
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"定时任务检查失败: {e}")
        return None