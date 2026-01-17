from django.core.management.base import BaseCommand
from syncservice.models import SyncConfig


class Command(BaseCommand):
    help = '初始化同步配置'

    def handle(self, *args, **options):
        self.stdout.write('开始初始化同步配置...')

        # 配置分组定义
        config_groups = {
            # 系统功能开关
            'system_config': [
                ('hr_sync_enabled', 'true', '是否启用HR数据同步'),
                ('task_auto_creation_enabled', 'true', '是否启用账号任务自动创建'),
                ('task_processing_enabled', 'true', '是否启用账号任务处理'),
            ],

            # HR同步配置
            'hr_sync_config': [
                ('hieds_account', 'your_hieds_account', 'HIEDS API账号'),
                ('hieds_secret', 'your_hieds_secret', 'HIEDS API密钥'),
                ('hieds_project', 'your_project', 'HIEDS项目标识'),
                ('hieds_enterprise', 'your_enterprise', 'HIEDS企业标识'),
                ('hieds_person_project_id', 'your_person_project_id', 'HIEDS人员项目ID'),
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
                ('email_domain', '@qq.com', '邮箱域名'),
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

    def _mask_sensitive_value(self, key, value):
        """对敏感配置进行遮罩显示"""
        sensitive_keys = [
            'hieds_secret', 'idaas_secret', 'welink_client_secret',
            'email_auth_token', 'hieds_account', 'idaas_account'
        ]

        if key in sensitive_keys and len(value) > 4:
            return value[:2] + '*' * (len(value) - 4) + value[-2:]
        return value