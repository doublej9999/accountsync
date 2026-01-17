from django.db import models


class HrPersonAccount(models.Model):
    """人员账号模型"""
    ACCOUNT_TYPE_CHOICES = [
        ('idaas', 'IDAAS账号'),
        ('welink', 'Welink账号'),
        ('email', '邮箱账号'),
    ]

    # 关联人员
    person = models.ForeignKey('HrPerson', on_delete=models.CASCADE, related_name='accounts', verbose_name='人员')

    # 账号类型
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        verbose_name='账号类型'
    )

    # 账号标识
    account_identifier = models.CharField(max_length=200, blank=True, null=True, verbose_name='账号标识')

    # 创建状态
    is_created = models.BooleanField(default=True, verbose_name='是否已创建')

    # 账号创建时间
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '人员账号'
        verbose_name_plural = '人员账号'
        unique_together = ['person', 'account_type']  # 确保每人每种账号类型只有一条记录
        ordering = ['person', 'account_type']
        indexes = [
            models.Index(fields=['person', 'account_type']),
            models.Index(fields=['is_created']),
            models.Index(fields=['account_identifier']),  # 用于搜索优化
        ]

    def __str__(self):
        return f"{self.person.employee_number} - {self.get_account_type_display()}"

    @staticmethod
    def create_default_accounts(person):
        """为人员创建默认的三种账号记录"""
        account_types = ['idaas', 'welink', 'email']
        accounts_created = []

        for account_type in account_types:
            # 设置账号标识
            identifier = None
            if account_type == 'email' and person.email_address:
                identifier = person.email_address
            elif account_type in ['idaas', 'welink'] and person.employee_account:
                identifier = person.employee_account

            account, created = HrPersonAccount.objects.get_or_create(
                person=person,
                account_type=account_type,
                defaults={
                    'account_identifier': identifier,
                    'is_created': True  # 默认已创建
                }
            )

            if created:
                accounts_created.append(account)

        return accounts_created


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
            models.Index(fields=['full_name']),  # 用于搜索优化
            models.Index(fields=['english_name']),  # 用于搜索优化
            models.Index(fields=['email_address']),  # 用于搜索优化
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


class DepartmentMapping(models.Model):
    """部门映射表"""
    idata_departmentcode = models.CharField(max_length=50, unique=True, verbose_name='iData部门代码')
    idaas_departmentcode = models.CharField(max_length=50, verbose_name='IDAAS部门代码')
    ou = models.CharField(max_length=200, verbose_name='OU路径')

    class Meta:
        verbose_name = '部门映射'
        verbose_name_plural = '部门映射'
        ordering = ['idata_departmentcode']
        indexes = [
            models.Index(fields=['idata_departmentcode']),
            models.Index(fields=['idaas_departmentcode']),  # 用于搜索优化
            models.Index(fields=['ou']),  # 用于搜索优化
        ]

    def __str__(self):
        return f"{self.idata_departmentcode} -> {self.idaas_departmentcode}"


class AccountCreationTask(models.Model):
    """账号创建任务模型"""
    TASK_STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    task_id = models.CharField(max_length=100, unique=True, verbose_name='任务ID')
    person = models.ForeignKey('HrPerson', on_delete=models.CASCADE, related_name='creation_tasks', verbose_name='人员')
    account_type = models.CharField(
        max_length=20,
        choices=HrPersonAccount.ACCOUNT_TYPE_CHOICES,
        verbose_name='账号类型'
    )

    status = models.CharField(
        max_length=20,
        choices=TASK_STATUS_CHOICES,
        default='pending',
        verbose_name='任务状态'
    )

    result_data = models.JSONField(blank=True, null=True, verbose_name='结果数据')

    # 顺序控制
    depends_on_task = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='dependent_tasks',
        verbose_name='依赖任务'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='完成时间')

    class Meta:
        verbose_name = '账号创建任务'
        verbose_name_plural = '账号创建任务'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['person', 'account_type']),
            models.Index(fields=['task_id']),
        ]
        unique_together = ['person', 'account_type', 'depends_on_task']

    def __str__(self):
        return f"{self.person.employee_number} - {self.get_account_type_display()} - {self.get_status_display()}"

    def can_process(self):
        """检查任务是否可以处理"""
        if self.status != 'pending':
            return False

        # 如果有依赖任务，检查依赖任务是否已完成
        if self.depends_on_task:
            return self.depends_on_task.status == 'completed'

        return True

    def mark_processing(self):
        """标记为处理中"""
        self.status = 'processing'
        self.save()

    def mark_completed(self, result_data=None):
        """标记为完成"""
        self.status = 'completed'
        self.result_data = result_data
        self.completed_at = timezone.now()
        self.save()

    @property
    def retry_count(self):
        """动态计算重试次数（通过日志数量）"""
        return self.error_logs.count()

    @property
    def max_retries(self):
        """从环境变量获取最大重试次数"""
        import os
        return int(os.getenv('ACCOUNT_CREATION_MAX_RETRIES', '5'))

    def should_retry(self):
        """检查是否应该重试"""
        return self.status == 'failed' and self.retry_count < self.max_retries

    def mark_failed(self, error_message, error_details=None, execution_context=None):
        """标记为失败并记录错误日志"""
        import traceback
        from syncservice.models import AccountCreationLog

        self.status = 'failed'
        self.save()

        # 创建错误日志记录
        execution_attempt = self.retry_count + 1  # 当前执行次数
        AccountCreationLog.objects.create(
            task=self,
            execution_attempt=execution_attempt,
            error_message=error_message,
            error_details={
                'error_type': type(error_details).__name__ if error_details else 'Exception',
                'stack_trace': traceback.format_exc(),
                'additional_info': error_details
            } if error_details or traceback.format_exc() != 'NoneType: None\n' else None,
            execution_context=execution_context
        )


class AccountCreationLog(models.Model):
    """账号创建任务执行日志 - 记录错误信息"""

    task = models.ForeignKey(AccountCreationTask, on_delete=models.CASCADE, related_name='error_logs', verbose_name='任务')
    execution_attempt = models.IntegerField(verbose_name='执行尝试次数')  # 从1开始计数

    # 错误信息
    error_message = models.TextField(verbose_name='错误信息')
    error_details = models.JSONField(blank=True, null=True, verbose_name='错误详情')  # 存储堆栈跟踪、API响应等

    # 执行上下文（可选，用于存储关键执行数据）
    execution_context = models.JSONField(blank=True, null=True, verbose_name='执行上下文')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '账号创建日志'
        verbose_name_plural = '账号创建日志'
        ordering = ['task', 'execution_attempt']
        unique_together = ['task', 'execution_attempt']  # 确保每轮执行只有一个日志
        indexes = [
            models.Index(fields=['task', 'execution_attempt']),
            models.Index(fields=['error_message']),  # 用于搜索优化
        ]

    def __str__(self):
        return f"{self.task.task_id} - 第{self.execution_attempt}次执行 - {self.error_message[:50]}..."