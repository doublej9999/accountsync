from django.core.management.base import BaseCommand
from syncservice.models import SyncConfig, PersonTypeMapping


class Command(BaseCommand):
    help = '初始化系统数据（同步配置和人员类型映射）'

    def handle(self, *args, **options):
        self.stdout.write('开始初始化系统数据...')

        # 第一阶段：初始化同步配置
        self._init_sync_config()

        # 第二阶段：初始化人员类型映射
        self._init_person_type_mappings()

        # 输出最终统计
        total_configs = SyncConfig.objects.count()
        total_mappings = PersonTypeMapping.objects.count()

        self.stdout.write(
            self.style.SUCCESS(
                f'\n系统数据初始化完成\n'
                f'总配置项: {total_configs}\n'
                f'总映射记录: {total_mappings}'
            )
        )

    def _init_sync_config(self):
        """初始化同步配置"""
        self.stdout.write('\n开始初始化同步配置...')

        # 配置分组定义
        config_groups = {
            # 系统功能开关
            'system_config': [
                ('hr_sync_enabled', 'false', '是否启用HR数据同步'),
                ('task_auto_creation_enabled', 'false', '是否启用账号任务自动创建'),
                ('task_processing_enabled', 'false', '是否启用账号任务处理'),
            ],

            # HR同步配置
            'hr_sync_config': [
                ('hieds_account', 'your_hieds_account', 'HIEDS API账号'),
                ('hieds_secret', 'your_hieds_secret', 'HIEDS API密钥'),
                ('hieds_project', 'your_project', 'HIEDS项目标识'),
                ('hieds_enterprise', 'your_enterprise', 'HIEDS企业标识'),
                ('hieds_tenant_id', 'your_tenant_id', 'HIEDS租户ID'),
                ('hieds_page_size', '20', 'HIEDS分页大小'),
                ('valid_employee_statuses', '["1"]', '有效的员工状态列表（JSON格式）'),
            ],

            # 任务处理配置
            'task_config': [
                ('account_creation_max_retries', '5', '账号创建最大重试次数'),
            ],

            # IDAAS配置
            'idaas_config': [
                ('idaas_account', 'your_idaas_account', 'IDAAS账号'),
                ('idaas_secret', 'your_idaas_secret', 'IDAAS密钥'),
                ('idaas_enterprise_id', 'your_enterprise_id', 'IDAAS企业ID'),
            ],

            # Welink配置
            'welink_config': [
                ('welink_client_id', 'your_welink_client_id', 'Welink客户端ID'),
                ('welink_client_secret', 'your_welink_client_secret', 'Welink客户端密钥'),
            ],

            # 邮箱配置
            'email_config': [
                ('default_email_domain', '@qq.com', '默认邮箱域名（当person_type无映射时使用）'),
                ('email_auth_token', 'abcdefghijklmnopqrstuvwsyz', '邮箱认证令牌'),
            ]
        }

        # 初始化所有配置
        total_configs = 0
        for group_name, configs in config_groups.items():
            self.stdout.write(f'\n初始化 {group_name} 配置:')
            for key, default_value, description in configs:
                config = SyncConfig.set_config(key, default_value, description)
                self.stdout.write(f'  {key}: {self._mask_sensitive_value(key, config.value)}')
                total_configs += 1

        self.stdout.write(self.style.SUCCESS(f'\n同步配置初始化完成，共初始化 {total_configs} 个配置项'))

    def _init_person_type_mappings(self):
        """初始化人员类型映射数据"""
        self.stdout.write('\n开始初始化人员类型映射数据...')

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

    def _mask_sensitive_value(self, key, value):
        """对敏感配置进行遮罩显示"""
        sensitive_keys = [
            'hieds_secret', 'idaas_secret', 'welink_client_secret',
            'email_auth_token', 'hieds_account', 'idaas_account'
        ]

        if key in sensitive_keys and len(value) > 4:
            return value[:2] + '*' * (len(value) - 4) + value[-2:]
        return value