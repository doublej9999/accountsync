import os
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from syncservice.models import HrPerson, AccountCreationTask, SyncConfig, AccountCreationRequest, AccountCreationRequestItem
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
            # 第一步：处理账号创建请求中的用户
            self.stdout.write('\n=== 处理账号创建请求中的用户 ===')
            created_tasks_for_requests = self._process_account_creation_requests(dry_run)

            # 第二步：处理HR同步的用户
            self.stdout.write('\n=== 处理HR同步的用户 ===')

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

                self.stdout.write(f'\nHR同步用户总计将创建 {total_tasks} 个账号任务')
                self.stdout.write(f'\n账号创建请求总计将创建 {created_tasks_for_requests} 个账号任务')
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

            total_created = len(created_tasks) + created_tasks_for_requests
            self.stdout.write(
                self.style.SUCCESS(f'\n创建完成: HR同步用户 {len(created_tasks)} 个，账号创建请求 {created_tasks_for_requests} 个，总计 {total_created} 个账号任务')
            )

        except Exception as e:
            logger.error(f'创建账号任务失败: {e}')
            raise CommandError(f'创建账号任务失败: {str(e)}')

    def _process_account_creation_requests(self, dry_run=False):
        """处理账号创建请求，为已同步的用户创建账号任务"""
        total_created = 0

        # 获取所有 processing 状态且已同步完成的请求
        requests = AccountCreationRequest.objects.filter(status='processing')

        if not requests.exists():
            self.stdout.write('没有待处理的账号创建请求')
            return total_created

        self.stdout.write(f'找到 {requests.count()} 个待处理的账号创建请求')

        for request in requests:
            self.stdout.write(f'\n处理请求: {request.request_id}')

            # 获取已同步但未创建任务的请求项
            items = request.items.filter(status='synced')

            if not items.exists():
                # 检查是否所有请求项都已处理完成
                total_items = request.items.count()
                processed_items = request.items.exclude(status__in=['synced']).count()

                if total_items == processed_items:
                    # 所有请求项都已处理完成，更新请求状态
                    self._update_request_status(request)
                continue

            # 为这些用户创建账号任务
            request_task_count = 0
            for item in items:
                if not item.hr_person:
                    continue

                person = item.hr_person
                system_list = request.system_list

                # 获取需要创建的任务类型
                tasks_for_person = self._get_tasks_for_person(person, system_list)
                if not tasks_for_person:
                    continue

                if dry_run:
                    self.stdout.write(f'  预览: 为 {person.employee_number} 创建任务: {", ".join(tasks_for_person)}')
                    request_task_count += len(tasks_for_person)
                else:
                    # 创建账号任务
                    person_tasks = self._create_tasks_for_person(person, tasks_for_person)
                    request_task_count += len(person_tasks)

                    # 更新请求项状态
                    item.status = 'task_created'
                    item.save()

                    self.stdout.write(f'  为 {person.employee_number} 创建了 {len(person_tasks)} 个任务')

            total_created += request_task_count

            # 更新请求状态
            if not dry_run:
                self._update_request_status(request)

        return total_created

    def _update_request_status(self, request):
        """更新请求状态"""
        total_items = request.items.count()
        synced_items = request.items.filter(status__in=['synced', 'task_created', 'completed']).count()
        failed_items = request.items.filter(status='failed').count()
        request.processed_users = synced_items + failed_items
        request.save()

        # 检查是否所有请求项都已处理完成
        if synced_items + failed_items == total_items:
            if failed_items > 0:
                request.update_status('partial_failed')
            else:
                request.update_status('completed')
            self.stdout.write(f'请求 {request.request_id} 状态已更新为: {request.get_status_display()}')

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
            task_id = f"{person.employee_number}_{account_type}_{int(timestamp)}"

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