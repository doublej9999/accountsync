import os
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from syncservice.models import HrPerson, AccountCreationTask, SyncConfig
from syncservice.services import ConfigService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '创建账号创建任务'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示将创建的任务，不实际创建',
        )
        parser.add_argument(
            '--employee-status',
            nargs='+',
            help='指定员工状态，多个状态用空格分隔',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        employee_status_filter = options.get('employee_status')

        self.stdout.write('开始创建账号任务...')

        try:
            # 获取需要处理的员工状态
            if employee_status_filter:
                employee_status_list = employee_status_filter
                self.stdout.write(f'指定员工状态: {", ".join(employee_status_list)}')
            else:
                # 从配置中获取有效的员工状态
                employee_status_list = ConfigService.get_json_config('valid_employee_statuses', ['1'])
                self.stdout.write(f'默认员工状态: {", ".join(employee_status_list)}')

            # 查询符合条件的HR人员
            persons_query = HrPerson.objects.filter(employee_status__in=employee_status_list)

            # 获取系统配置中启用的账号类型
            enabled_account_types = self._get_enabled_account_types()

            total_persons = persons_query.count()
            self.stdout.write(f'找到 {total_persons} 个符合条件的员工')

            if dry_run:
                self.stdout.write('\n=== 预览模式 - 以下是将被创建的任务 ===')
                total_tasks = 0

                for person in persons_query:
                    tasks_for_person = self._get_tasks_for_person(person, enabled_account_types)
                    if tasks_for_person:
                        self.stdout.write(f'员工 {person.employee_number} ({person.full_name}):')
                        for account_type in tasks_for_person:
                            self.stdout.write(f'  - {account_type}')
                            total_tasks += 1

                self.stdout.write(f'\n总计将创建 {total_tasks} 个账号任务')
                return

            # 执行模式
            created_tasks = []

            for person in persons_query:
                tasks_for_person = self._get_tasks_for_person(person, enabled_account_types)
                if not tasks_for_person:
                    continue

                # 为员工创建账号任务
                person_tasks = self._create_tasks_for_person(person, tasks_for_person)
                created_tasks.extend(person_tasks)

                self.stdout.write(f'为员工 {person.employee_number} ({person.full_name}) 创建了 {len(person_tasks)} 个任务')

            self.stdout.write(
                self.style.SUCCESS(f'\n创建完成: 总计创建 {len(created_tasks)} 个账号任务')
            )

        except Exception as e:
            logger.error(f'创建账号任务失败: {e}')
            raise CommandError(f'创建账号任务失败: {str(e)}')

    def _get_enabled_account_types(self):
        """获取启用的账号类型"""
        # 从配置中获取启用的账号类型，默认启用所有
        enabled_types = ConfigService.get_config('enabled_account_types', 'idaas,welink,email')
        return [t.strip() for t in enabled_types.split(',')]

    def _get_tasks_for_person(self, person, enabled_account_types):
        """获取为指定人员需要创建的任务类型"""
        tasks_to_create = []

        for account_type in enabled_account_types:
            # 检查是否已存在该类型的任务
            existing_task = AccountCreationTask.objects.filter(
                person=person,
                account_type=account_type,
            ).exists()

            if not existing_task:
                tasks_to_create.append(account_type)

        return tasks_to_create

    def _create_tasks_for_person(self, person, account_types):
        """为指定人员创建账号任务"""
        created_tasks = []

        # 定义账号创建顺序
        account_order = {
            'idaas': 1,
            'welink': 2,
            'email': 3
        }

        # 按顺序排序
        sorted_account_types = sorted(account_types, key=lambda x: account_order.get(x, 999))

        previous_task = None

        for account_type in sorted_account_types:
            # 生成唯一的任务ID
            timestamp = timezone.now().timestamp()
            task_id = "06d"

            # 创建任务
            task = AccountCreationTask.objects.create(
                task_id=task_id,
                person=person,
                account_type=account_type,
                depends_on_task=previous_task
            )

            created_tasks.append(task)
            previous_task = task

            logger.info(f'创建任务: {task_id} - {person.employee_number} - {account_type}')

        return created_tasks