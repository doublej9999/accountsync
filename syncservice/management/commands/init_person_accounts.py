from django.core.management.base import BaseCommand, CommandError
from syncservice.models import HrPerson, HrPersonAccount


class Command(BaseCommand):
    help = '初始化人员账号数据（首次全量同步，创建idaas和welink账号记录）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='模拟运行，不实际创建账号记录',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== 模拟运行模式 ==='))

        self.stdout.write('开始初始化人员账号数据...\n')

        # 获取所有人员
        all_persons = HrPerson.objects.all()
        total_persons = all_persons.count()

        if total_persons == 0:
            self.stdout.write(self.style.WARNING('没有找到任何人员记录，请先同步人员数据'))
            return

        self.stdout.write(f'找到 {total_persons} 个人员记录\n')

        # 统计信息
        stats = {
            'total_persons': total_persons,
            'idaas_created': 0,
            'idaas_existed': 0,
            'idaas_updated': 0,
            'welink_created': 0,
            'welink_existed': 0,
            'welink_updated': 0,
            'email_created': 0,
            'email_existed': 0,
            'errors': 0,
        }

        # 遍历所有人员
        for index, person in enumerate(all_persons, 1):
            try:
                if index % 100 == 0:
                    self.stdout.write(f'处理进度: {index}/{total_persons}')

                # 获取账号标识（使用工号）
                account_identifier = person.employee_number

                if not account_identifier:
                    self.stdout.write(
                        self.style.WARNING(f'  跳过人员 {person.person_id}（{person.full_name}）: 工号为空')
                    )
                    stats['errors'] += 1
                    continue

                # 1. 创建或更新 IDAAS 账号记录
                if not dry_run:
                    idaas_account, idaas_created = HrPersonAccount.objects.get_or_create(
                        person=person,
                        account_type='idaas',
                        defaults={
                            'account_identifier': account_identifier,
                            'is_created': True  # 初始化时标记为未创建
                        }
                    )

                    if idaas_created:
                        stats['idaas_created'] += 1
                    else:
                        # 如果已存在，检查是否需要更新标识
                        if idaas_account.account_identifier != account_identifier:
                            idaas_account.account_identifier = account_identifier
                            idaas_account.save()
                            stats['idaas_updated'] += 1
                        else:
                            stats['idaas_existed'] += 1
                else:
                    # 模拟运行，检查是否存在
                    exists = HrPersonAccount.objects.filter(
                        person=person,
                        account_type='idaas'
                    ).exists()
                    if exists:
                        stats['idaas_existed'] += 1
                    else:
                        stats['idaas_created'] += 1

                # 2. 创建或更新 Welink 账号记录
                if not dry_run:
                    welink_account, welink_created = HrPersonAccount.objects.get_or_create(
                        person=person,
                        account_type='welink',
                        defaults={
                            'account_identifier': account_identifier,
                            'is_created': True  # 初始化时标记为未创建
                        }
                    )

                    if welink_created:
                        stats['welink_created'] += 1
                    else:
                        # 如果已存在，检查是否需要更新标识
                        if welink_account.account_identifier != account_identifier:
                            welink_account.account_identifier = account_identifier
                            welink_account.save()
                            stats['welink_updated'] += 1
                        else:
                            stats['welink_existed'] += 1
                else:
                    # 模拟运行，检查是否存在
                    exists = HrPersonAccount.objects.filter(
                        person=person,
                        account_type='welink'
                    ).exists()
                    if exists:
                        stats['welink_existed'] += 1
                    else:
                        stats['welink_created'] += 1

                # 3. 创建邮箱账号记录（标识置为空，允许后续同步）
                if not dry_run:
                    email_account, email_created = HrPersonAccount.objects.get_or_create(
                        person=person,
                        account_type='email',
                        defaults={
                            'account_identifier': None,  # 邮箱账号标识置为空
                            'is_created': True  # 初始化时标记为未创建
                        }
                    )

                    if email_created:
                        stats['email_created'] += 1
                    else:
                        stats['email_existed'] += 1
                else:
                    # 模拟运行，检查是否存在
                    exists = HrPersonAccount.objects.filter(
                        person=person,
                        account_type='email'
                    ).exists()
                    if exists:
                        stats['email_existed'] += 1
                    else:
                        stats['email_created'] += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  处理人员 {person.employee_number}（{person.full_name}）失败: {e}'
                    )
                )
                stats['errors'] += 1
                continue

        # 输出统计信息
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('初始化完成！'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'\n总人员数: {stats["total_persons"]}')
        self.stdout.write('\nIDaas 账号:')
        self.stdout.write(f'  新创建: {stats["idaas_created"]}')
        self.stdout.write(f'  已存在: {stats["idaas_existed"]}')
        self.stdout.write(f'  已更新: {stats["idaas_updated"]}')
        self.stdout.write('\nWelink 账号:')
        self.stdout.write(f'  新创建: {stats["welink_created"]}')
        self.stdout.write(f'  已存在: {stats["welink_existed"]}')
        self.stdout.write(f'  已更新: {stats["welink_updated"]}')
        self.stdout.write('\n邮箱账号:')
        self.stdout.write(f'  新创建: {stats["email_created"]}')
        self.stdout.write(f'  已存在: {stats["email_existed"]}')
        self.stdout.write(f'\n错误数: {stats["errors"]}')
        self.stdout.write('=' * 60)

        if dry_run:
            self.stdout.write(self.style.WARNING('\n注意: 这是模拟运行，未实际创建任何记录'))
