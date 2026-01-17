from django.core.management.base import BaseCommand, CommandError
from syncservice.models import DepartmentMapping

DEPARTMENT_DATA = [
    {
        'idata_departmentcode': '120000',
        'idaas_departmentcode': '120000',
        'ou': 'OU=外部公司人员，DC=yourdomain,DC=com'
    },
    # 添加更多部门映射数据
]


class Command(BaseCommand):
    help = '加载部门映射数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清除现有数据后重新加载',
        )

    def handle(self, *args, **options):
        if options['clear']:
            DepartmentMapping.objects.all().delete()
            self.stdout.write('已清除现有部门映射数据')

        created_count = 0
        updated_count = 0

        for dept_data in DEPARTMENT_DATA:
            dept, created = DepartmentMapping.objects.get_or_create(
                idata_departmentcode=dept_data['idata_departmentcode'],
                defaults=dept_data
            )

            if created:
                created_count += 1
                self.stdout.write(f'创建部门映射: {dept.idata_departmentcode}')
            else:
                # 更新现有记录
                dept.idaas_departmentcode = dept_data['idaas_departmentcode']
                dept.ou = dept_data['ou']
                dept.save()
                updated_count += 1
                self.stdout.write(f'更新部门映射: {dept.idata_departmentcode}')

        self.stdout.write(
            self.style.SUCCESS(f'部门映射数据加载完成: 创建 {created_count} 个, 更新 {updated_count} 个')
        )