from django.core.management.base import BaseCommand
from syncservice.models import PersonTypeMapping


class Command(BaseCommand):
    help = '初始化人员类型映射数据'

    def handle(self, *args, **options):
        self.stdout.write('开始初始化人员类型映射数据...')

        # 默认映射数据
        default_mappings = [
            {
                'person_type': '10',
                'email_domain': '@qq.com',
                'idaas_user_type': 'employee',
                'welink_person_type': '正式员工',
                'description': '正式员工'
            },
            {
                'person_type': '11',
                'email_domain': '@partner.com',
                'idaas_user_type': 'supplier',
                'welink_person_type': '外包',
                'description': '外包人员'
            },
            {
                'person_type': '12',
                'email_domain': '@intern.com',
                'idaas_user_type': 'intern',
                'welink_person_type': '实习生',
                'description': '实习生'
            },
            {
                'person_type': '13',
                'email_domain': '@contractor.com',
                'idaas_user_type': 'contractor',
                'welink_person_type': '顾问',
                'description': '外部顾问'
            },
        ]

        created_count = 0
        updated_count = 0

        for mapping_data in default_mappings:
            person_type = mapping_data['person_type']
            mapping, created = PersonTypeMapping.objects.get_or_create(
                person_type=person_type,
                defaults=mapping_data
            )

            if created:
                created_count += 1
                self.stdout.write(f'  创建映射: {person_type} -> {mapping_data["email_domain"]}')
            else:
                # 更新现有记录
                updated = False
                for key, value in mapping_data.items():
                    if getattr(mapping, key) != value:
                        setattr(mapping, key, value)
                        updated = True

                if updated:
                    mapping.save()
                    updated_count += 1
                    self.stdout.write(f'  更新映射: {person_type} -> {mapping_data["email_domain"]}')

        self.stdout.write(
            self.style.SUCCESS(
                f'\n人员类型映射初始化完成\n'
                f'新增: {created_count} 条\n'
                f'更新: {updated_count} 条\n'
                f'总计: {PersonTypeMapping.objects.count()} 条映射记录'
            )
        )