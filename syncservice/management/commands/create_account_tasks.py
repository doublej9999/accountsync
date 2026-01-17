from django.core.management.base import BaseCommand, CommandError
from syncservice.models import HrPerson, AccountCreationTask, SyncConfig
import json
import uuid


class AccountTaskCreator:
    """账号任务创建器"""

    def __init__(self, dry_run=False, valid_statuses=None, stdout=None):
        self.dry_run = dry_run
        self.valid_statuses = valid_statuses or self._get_valid_employee_statuses()
        self.stdout = stdout

    def create_pending_tasks(self):
        """创建待处理的账号任务"""
        # 筛选目标人员
        target_persons = HrPerson.objects.filter(
            employee_status__in=self.valid_statuses,
            employee_number__isnull=False,
            person_dept__isnull=False,
        )

        created_count = 0
        processed_count = 0

        for person in target_persons:
            try:
                processed_count += 1

                # 获取部门代码
                department_code = self._get_department_code(person)
                if not department_code:
                    continue

                # 检查并创建各种账号类型
                if self._needs_account_creation(person, 'idaas'):
                    if self._create_task(person, 'idaas', department_code):
                        created_count += 1

                if self._needs_account_creation(person, 'welink'):
                    if self._create_task(person, 'welink', department_code):
                        created_count += 1

                # Email任务依赖IDAAS任务
                if self._needs_account_creation(person, 'email'):
                    idaas_task = self._get_existing_task(person, 'idaas')
                    if self._create_task(person, 'email', department_code, depends_on=idaas_task):
                        created_count += 1

            except Exception as e:
                if self.stdout:
                    self.stdout.write(
                        self.style.ERROR(f"为人员 {person.employee_number} 创建任务失败: {e}")
                    )

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
        if self.dry_run:
            if self.stdout:
                self.stdout.write(
                    f'[预览] 将为 {person.employee_number} 创建 {account_type} 任务'
                )
            return True

        task_id = f"{person.employee_number}_{account_type}_{uuid.uuid4().hex[:8]}"

        task = AccountCreationTask.objects.create(
            task_id=task_id,
            person=person,
            account_type=account_type,
            depends_on_task=depends_on,
            status='pending'
        )

        if self.stdout:
            self.stdout.write(
                f'创建账号任务: {task_id} - {person.employee_number} - {account_type}'
            )
        return True


class Command(BaseCommand):
    help = '为有效员工创建账号创建任务'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='预览模式，只显示将要创建的任务，不实际执行',
        )
        parser.add_argument(
            '--employee-status',
            nargs='+',
            help='指定有效的员工状态，默认为配置中的值',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        custom_statuses = options.get('employee_status')

        self.stdout.write('开始创建账号任务...')

        try:
            # 创建任务创建器
            creator = AccountTaskCreator(
                dry_run=dry_run,
                valid_statuses=custom_statuses,
                stdout=self.stdout
            )

            # 执行任务创建
            created_count = creator.create_pending_tasks()

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f'预览完成，将创建 {created_count} 个账号任务')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'任务创建完成，成功创建 {created_count} 个账号任务')
                )

        except Exception as e:
            raise CommandError(f'创建账号任务失败: {e}')