from django.db import models


class HrPerson(models.Model):
    """人员信息模型"""
    # 基本标识
    person_id = models.IntegerField(primary_key=True, verbose_name='人员ID')
    employee_number = models.CharField(max_length=50, unique=True, verbose_name='员工编号')

    # 基本信息
    full_name = models.CharField(max_length=100, verbose_name='全名')
    english_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='英文名')
    sex = models.CharField(max_length=20, blank=True, null=True, verbose_name='性别')
    birth_day = models.DateField(blank=True, null=True, verbose_name='出生日期')
    nationality_code = models.CharField(max_length=10, blank=True, null=True, verbose_name='国籍代码')

    # 工作信息
    person_type = models.CharField(max_length=10, verbose_name='人员类型')
    employee_status = models.CharField(max_length=10, verbose_name='员工状态')
    employee_account = models.CharField(max_length=50, blank=True, null=True, verbose_name='员工账户')
    user_id = models.CharField(max_length=50, blank=True, null=True, verbose_name='用户ID')
    employee_description = models.TextField(blank=True, null=True, verbose_name='员工描述')

    # 联系信息
    email_address = models.EmailField(blank=True, null=True, verbose_name='邮箱')
    telephone_number1 = models.CharField(max_length=20, blank=True, null=True, verbose_name='电话1')
    telephone_number2 = models.CharField(max_length=20, blank=True, null=True, verbose_name='电话2')
    telephone_number3 = models.CharField(max_length=20, blank=True, null=True, verbose_name='电话3')
    full_address = models.TextField(blank=True, null=True, verbose_name='完整地址')
    postal_code = models.CharField(max_length=10, blank=True, null=True, verbose_name='邮政编码')
    base_location = models.CharField(max_length=100, blank=True, null=True, verbose_name='基地位置')

    # 财务信息
    expense_account = models.CharField(max_length=50, blank=True, null=True, verbose_name='费用账户')

    # 拼音和别名
    person_pinyin_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='人员拼音名')

    # 日期信息
    original_hire_date = models.DateField(blank=True, null=True, verbose_name='原始入职日期')
    creation_date = models.DateTimeField(verbose_name='创建日期')
    last_update_date = models.DateTimeField(verbose_name='最后更新日期')
    effective_date = models.DateField(blank=True, null=True, verbose_name='生效日期')
    disable_date = models.DateField(blank=True, null=True, verbose_name='禁用日期')

    # 部门信息 (JSON格式存储)
    person_dept = models.JSONField(verbose_name='部门信息')

    # 租户信息
    tenant_id = models.CharField(max_length=50, verbose_name='租户ID')

    # 元数据
    created_by = models.CharField(max_length=20, verbose_name='创建人')
    last_updated_by = models.CharField(max_length=20, verbose_name='最后更新人')

    class Meta:
        ordering = ['-creation_date']
        verbose_name = '人员信息'
        verbose_name_plural = '人员信息'
        indexes = [
            models.Index(fields=['employee_number']),
            models.Index(fields=['creation_date']),
            models.Index(fields=['last_update_date']),
        ]

    def __str__(self):
        return f"{self.employee_number} - {self.full_name}"


class SyncConfig(models.Model):
    """同步配置模型"""
    key = models.CharField(max_length=100, unique=True, verbose_name='配置键')
    value = models.TextField(verbose_name='配置值')
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name='描述')

    class Meta:
        verbose_name = '同步配置'
        verbose_name_plural = '同步配置'

    def __str__(self):
        return self.key

    @staticmethod
    def get_config(key, default=None):
        """获取配置值"""
        try:
            config = SyncConfig.objects.get(key=key)
            return config.value
        except SyncConfig.DoesNotExist:
            return default

    @staticmethod
    def set_config(key, value, description=None):
        """设置配置值"""
        config, created = SyncConfig.objects.get_or_create(
            key=key,
            defaults={'value': value, 'description': description}
        )
        if not created:
            config.value = value
            if description:
                config.description = description
            config.save()
        return config