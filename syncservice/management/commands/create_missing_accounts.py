from django.core.management.base import BaseCommand, CommandError

from syncservice.models import HrPerson, HrPersonAccount


class Command(BaseCommand):
    help = '为现有人员补全账号记录'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示将要执行的操作，不实际执行',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write('开始检查现有人员账号记录...')

        # 获取所有人员
        all_persons = HrPerson.objects.all()
        total_persons = all_persons.count()

        # 统计账号记录
        existing_accounts = HrPersonAccount.objects.all()
        self.stdout.write(f'现有人员总数: {total_persons}')
        self.stdout.write(f'现有账号记录总数: {existing_accounts.count()}')

        # 检查每个人员是否拥有三种账号类型
        missing_accounts = []
        for person in all_persons:
            existing_types = set(person.accounts.values_list('account_type', flat=True))
            expected_types = {'idaas', 'welink', 'email'}
            missing_types = expected_types - existing_types

            if missing_types:
                missing_accounts.append((person, missing_types))

        self.stdout.write(f'需要补全账号的人员数量: {len(missing_accounts)}')

        if dry_run:
            self.stdout.write('\n=== 预览模式 - 以下是将被创建的账号记录 ===')
            for person, missing_types in missing_accounts:
                for account_type in missing_types:
                    self.stdout.write(f'  {person.employee_number} - {person.full_name}: {account_type}')
        else:
            self.stdout.write('\n开始创建缺失的账号记录...')
            created_count = 0

            for person, missing_types in missing_accounts:
                for account_type in missing_types:
                    # 设置账号标识
                    identifier = None
                    if account_type == 'email' and person.email_address:
                        identifier = person.email_address
                    elif account_type in ['idaas', 'welink'] and person.employee_account:
                        identifier = person.employee_account

                    try:
                        account, created = HrPersonAccount.objects.get_or_create(
                            person=person,
                            account_type=account_type,
                            defaults={
                                'account_identifier': identifier,
                                'is_created': True  # 默认已创建
                            }
                        )

                        if created:
                            created_count += 1
                            self.stdout.write(f'创建账号: {person.employee_number} - {account_type}')
                        else:
                            self.stdout.write(f'账号已存在: {person.employee_number} - {account_type}')

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'创建账号失败: {person.employee_number} - {account_type}, 错误: {e}')
                        )

            self.stdout.write(self.style.SUCCESS(f'账号补全完成，共创建 {created_count} 个账号记录'))

        # 显示最终统计
        self.stdout.write('\n=== 最终统计 ===')
        final_accounts = HrPersonAccount.objects.all()
        self.stdout.write(f'人员总数: {total_persons}')
        self.stdout.write(f'账号记录总数: {final_accounts.count()}')

        # 按类型统计
        for account_type, display_name in HrPersonAccount.ACCOUNT_TYPE_CHOICES:
            count = final_accounts.filter(account_type=account_type).count()
            self.stdout.write(f'{display_name}: {count} 个')