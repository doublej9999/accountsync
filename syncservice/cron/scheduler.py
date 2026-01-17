from django.core.management import call_command
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging
import json
from syncservice.models import HrPerson, AccountCreationTask, SyncConfig

logger = logging.getLogger(__name__)


class AccountTaskCreator:
    """账号任务创建器"""

    def create_pending_tasks(self):
        """创建待处理的账号任务"""
        valid_statuses = self._get_valid_employee_statuses()

        # 筛选目标人员
        target_persons = HrPerson.objects.filter(
            employee_status__in=valid_statuses,
            employee_number__isnull=False,
            person_dept__isnull=False,
        )

        created_count = 0

        for person in target_persons:
            try:
                # 获取部门代码
                department_code = self._get_department_code(person)
                if not department_code:
                    continue

                # 创建IDAAS任务
                if self._needs_account_creation(person, 'idaas'):
                    self._create_task(person, 'idaas', department_code)
                    created_count += 1

                # 创建Welink任务
                if self._needs_account_creation(person, 'welink'):
                    self._create_task(person, 'welink', department_code)
                    created_count += 1

                # 创建Email任务（依赖IDAAS任务）
                if self._needs_account_creation(person, 'email'):
                    idaas_task = self._get_existing_task(person, 'idaas')
                    self._create_task(person, 'email', department_code, depends_on=idaas_task)
                    created_count += 1

            except Exception as e:
                logger.error(f"为人员 {person.employee_number} 创建任务失败: {e}")

        return created_count

    def _get_valid_employee_statuses(self):
        """获取有效的员工状态列表"""
        config_value = SyncConfig.get_config('valid_employee_statuses', '["1"]')
        try:
            return json.loads(config_value)
        except (json.JSONDecodeError, TypeError):
            return ['1']

    def _get_department_code(self, person):
        """从人员信息中提取部门代码"""
        if not person.person_dept or not isinstance(person.person_dept, list):
            return None

        if person.person_dept:
            dept_info = person.person_dept[0] if isinstance(person.person_dept, list) else person.person_dept
            return dept_info.get('department_code') if isinstance(dept_info, dict) else None

        return None

    def _needs_account_creation(self, person, account_type):
        """检查是否需要创建账号"""
        return not AccountCreationTask.objects.filter(
            person=person,
            account_type=account_type,
            status__in=['pending', 'processing', 'completed']
        ).exists()

    def _get_existing_task(self, person, account_type):
        """获取已存在的任务（用于依赖关系）"""
        try:
            return AccountCreationTask.objects.get(
                person=person,
                account_type=account_type,
                status__in=['pending', 'processing', 'completed']
            )
        except AccountCreationTask.DoesNotExist:
            return None

    def _create_task(self, person, account_type, department_code, depends_on=None):
        """创建单个任务"""
        import uuid
        task_id = f"{person.employee_number}_{account_type}_{uuid.uuid4().hex[:8]}"

        task = AccountCreationTask.objects.create(
            task_id=task_id,
            person=person,
            account_type=account_type,
            depends_on_task=depends_on,
            status='pending'
        )

        logger.info(f"创建账号任务: {task_id} - {person.employee_number} - {account_type}")
        return task


class TaskCreationScheduler:
    """任务创建定时器 - 专门负责自动创建账号任务"""

    def __init__(self):
        self.interval_minutes = getattr(settings, 'TASK_CREATION_CHECK_INTERVAL_MINUTES', 10)
        self.last_run = None

    def should_run(self):
        """检查是否应该运行任务创建"""
        if not self._is_enabled():
            return False

        if self.last_run is None:
            return True

        next_run = self.last_run + timedelta(minutes=self.interval_minutes)
        return timezone.now() >= next_run

    def run_task_creation(self):
        """执行任务创建"""
        try:
            logger.info("开始自动创建账号任务")
            call_command('create_account_tasks')
            self.last_run = timezone.now()
            logger.info("自动创建账号任务完成")
        except Exception as e:
            logger.error(f"自动创建账号任务失败: {e}")

    def _is_enabled(self):
        """检查是否启用任务自动创建"""
        config_value = SyncConfig.get_config('task_auto_creation_enabled', 'true')
        return config_value.lower() == 'true'


class HrSyncScheduler:
    """人员同步定时器"""

    def __init__(self):
        self.interval_minutes = getattr(settings, 'HR_SYNC_INTERVAL_MINUTES', 10)
        self.last_run = None

    def should_run(self):
        """检查是否应该运行同步"""
        if not self._is_sync_enabled():
            return False

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

    def _is_sync_enabled(self):
        """检查是否启用HR同步"""
        config_value = SyncConfig.get_config('hr_sync_enabled', 'true')
        return config_value.lower() == 'true'


class AccountCreationScheduler:
    """账号创建任务处理定时器 - 只负责处理现有任务"""

    def __init__(self):
        self.interval_minutes = getattr(settings, 'ACCOUNT_CREATION_INTERVAL_MINUTES', 5)
        self.last_run = None

    def should_run(self):
        """检查是否应该运行任务处理"""
        if not self._is_enabled():
            return False

        if self.last_run is None:
            return True

        next_run = self.last_run + timedelta(minutes=self.interval_minutes)
        return timezone.now() >= next_run

    def run_task_processing(self):
        """执行任务处理"""
        try:
            logger.info("开始处理账号创建任务")
            call_command('process_account_creation_tasks')
            self.last_run = timezone.now()
            logger.info("处理账号创建任务完成")
        except Exception as e:
            logger.error(f"处理账号创建任务失败: {e}")

    def _is_enabled(self):
        """检查是否启用任务处理"""
        config_value = SyncConfig.get_config('task_processing_enabled', 'true')
        return config_value.lower() == 'true'


# 全局调度器实例
hr_sync_scheduler = HrSyncScheduler()
task_creation_scheduler = TaskCreationScheduler()
account_creation_scheduler = AccountCreationScheduler()


def run_hr_sync_if_needed():
    """运行HR数据同步"""
    if hr_sync_scheduler.should_run():
        hr_sync_scheduler.run_sync()


def run_task_creation_if_needed():
    """运行任务自动创建"""
    if task_creation_scheduler.should_run():
        task_creation_scheduler.run_task_creation()


def run_account_creation_if_needed():
    """运行账号任务处理"""
    if account_creation_scheduler.should_run():
        account_creation_scheduler.run_task_processing()