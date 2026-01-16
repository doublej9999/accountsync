import os
from django.utils.deprecation import MiddlewareMixin
from syncservice.cron.scheduler import run_hr_sync_if_needed, run_account_creation_if_needed


class HrSyncMiddleware(MiddlewareMixin):
    """人员同步中间件 - 在请求中检查是否需要运行定时同步"""

    def __init__(self, get_response=None):
        super().__init__(get_response)
        # 初始化时读取同步开关状态
        self.sync_enabled = os.getenv('HR_SYNC_ENABLED', 'true').lower() in ('true', '1', 'yes', 'on')
        self.account_creation_enabled = os.getenv('ACCOUNT_CREATION_ENABLED', 'true').lower() in ('true', '1', 'yes', 'on')

    def process_request(self, request):
        # 检查同步是否启用
        if not self.sync_enabled:
            return None

        # 只在非静态文件请求时检查
        if not request.path.startswith('/static/') and not request.path.startswith('/media/'):
            try:
                run_hr_sync_if_needed()
                # 同时检查账号创建任务
                if self.account_creation_enabled:
                    run_account_creation_if_needed()
            except Exception as e:
                # 不让同步错误影响正常请求
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"定时同步检查失败: {e}")
        return None