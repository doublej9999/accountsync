from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from syncservice.models import AccountCreationTask, HrPersonAccount
from syncservice.services import AccountCreationService, ConfigService
import logging
import os

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '处理账号创建任务'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-tasks',
            type=int,
            default=50,
            help='每次运行最多处理的任务数量',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示将要执行的操作，不实际执行',
        )

    def handle(self, *args, **options):
        max_tasks = options['max_tasks']
        dry_run = options['dry_run']

        self.stdout.write('开始处理账号创建任务...')

        try:
            # 获取待处理的任务（重试次数小于最大重试次数）
            pending_tasks = AccountCreationTask.objects.filter(
                status__in=['pending', 'failed']
            ).order_by('created_at')[:max_tasks]

            # 过滤出重试次数未达到上限的任务
            max_retries = ConfigService.get_int_config('account_creation_max_retries', 5)
            filtered_tasks = []
            for task in pending_tasks:
                if task.status == 'pending' or task.retry_count < max_retries:
                    filtered_tasks.append(task)
                if len(filtered_tasks) >= max_tasks:
                    break

            pending_tasks = filtered_tasks

            self.stdout.write(f'找到 {len(pending_tasks)} 个待处理任务')

            if dry_run:
                self.stdout.write('\n=== 预览模式 - 以下是将被处理的任务 ===')
                for task in pending_tasks:
                    if task.can_process():
                        self.stdout.write(f'  {task.task_id}: {task.person.employee_number} - {task.get_account_type_display()}')
                    else:
                        self.stdout.write(f'  {task.task_id}: {task.person.employee_number} - {task.get_account_type_display()} (等待依赖任务)')
                return

            processed_count = 0
            success_count = 0
            failed_count = 0

            service = AccountCreationService()

            for task in pending_tasks:
                if not task.can_process():
                    self.stdout.write(f'跳过任务 {task.task_id}: 等待依赖任务完成')
                    continue

                try:
                    self.stdout.write(f'处理任务: {task.task_id} - {task.person.employee_number} - {task.get_account_type_display()}')

                    # 标记为处理中
                    task.mark_processing()

                    # 获取人员的部门代码
                    department_code = None
                    if task.person.person_dept and isinstance(task.person.person_dept, list) and task.person.person_dept:
                        # 假设部门信息在 person_dept 的第一个元素
                        dept_info = task.person.person_dept[0] if isinstance(task.person.person_dept, list) else task.person.person_dept
                        department_code = dept_info.get('department_code') if isinstance(dept_info, dict) else None

                    if not department_code:
                        # 尝试从其他字段获取部门代码
                        department_code = getattr(task.person, 'department_code', None)

                    if not department_code:
                        raise Exception(f"无法获取部门代码，跳过账号创建")

                    # 调用服务创建账号
                    result = service.create_account(task.person, task.account_type, department_code)

                    # 标记为完成
                    task.mark_completed(result)

                    # 更新 HrPersonAccount 记录
                    account, created = HrPersonAccount.objects.get_or_create(
                        person=task.person,
                        account_type=task.account_type,
                        defaults={
                            'account_identifier': result.get('account_identifier'),
                            'is_created': True
                        }
                    )

                    if not created:
                        account.account_identifier = result.get('account_identifier')
                        account.is_created = True
                        account.save()

                    self.stdout.write(
                        self.style.SUCCESS(f'任务完成: {task.task_id}')
                    )

                    success_count += 1

                except Exception as e:
                    error_msg = str(e)
                    self.stdout.write(
                        self.style.ERROR(f'任务失败: {task.task_id}, 错误: {error_msg}')
                    )

                    # 构建执行上下文
                    execution_context = {
                        'person_id': task.person.employee_number,
                        'account_type': task.account_type,
                        'department_code': department_code,
                        'execution_attempt': task.retry_count + 1,
                        'processed_at': timezone.now().isoformat()
                    }

                    # 标记为失败并记录日志
                    task.mark_failed(error_msg, error_details={'exception': error_msg}, execution_context=execution_context)

                    # 检查是否需要重试
                    if task.should_retry():
                        self.stdout.write(f'任务 {task.task_id} 将在下次运行时重试 (重试次数: {task.retry_count}/{task.max_retries})')
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'任务 {task.task_id} 达到最大重试次数，标记为最终失败')
                        )

                    failed_count += 1

                processed_count += 1

            self.stdout.write(
                self.style.SUCCESS(f'\n处理完成: 总计 {processed_count} 个任务，成功 {success_count} 个，失败 {failed_count} 个')
            )

        except Exception as e:
            logger.error(f"处理账号创建任务时发生错误: {e}")
            raise CommandError(f"处理账号创建任务失败: {e}")