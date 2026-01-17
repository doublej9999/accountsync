from django.contrib import admin, messages
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    RangeDateFilter,
    RangeDateTimeFilter,
    RangeNumericFilter,
    SingleNumericFilter
)
from unfold.paginator import InfinitePaginator

from syncservice.models import (
    HrPerson, HrPersonAccount, SyncConfig, DepartmentMapping,
    AccountCreationTask, AccountCreationLog
)
from syncservice.services import AccountCreationService


# Register your models here.
@admin.register(HrPerson)
class HrPersonAdmin(ModelAdmin):

    list_display = ['employee_number', 'full_name', 'employee_status', 'person_type', 'creation_date']
    list_filter = [
        'employee_status',
        'person_type',
        ('creation_date', RangeDateFilter),
        ('last_update_date', RangeDateFilter),
    ]
    search_fields = ['employee_number', 'full_name', 'english_name', 'email_address']
    readonly_fields = ['person_id', 'creation_date', 'last_update_date']
    list_per_page = 5  # 人员数据分页
    paginator = InfinitePaginator

    # Unfold specific configurations
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True
    list_filter_submit = True

    # 显示完整结果计数
    show_full_result_count = True


@admin.register(HrPersonAccount)
class HrPersonAccountAdmin(ModelAdmin):
    list_display = ['person', 'account_type', 'account_identifier', 'is_created', 'updated_at']
    list_filter = [
        'account_type',
        'is_created',
        ('updated_at', RangeDateTimeFilter),
        ('created_at', RangeDateTimeFilter),
    ]
    search_fields = ['person__employee_number', 'person__full_name', 'account_identifier']
    list_editable = ['is_created']
    raw_id_fields = ['person']
    list_per_page = 50  # 账号数据分页

    # Unfold specific configurations
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True
    list_filter_submit = True
    list_filter_sheet = False  # Use sidebar filters

    # 显示完整结果计数
    show_full_result_count = True

    def get_queryset(self, request):
        """优化查询，避免 N+1 查询"""
        return super().get_queryset(request).select_related('person')


@admin.register(SyncConfig)
class SyncConfigAdmin(ModelAdmin):
    list_display = ['key', 'get_config_category', 'get_value_preview', 'description']
    search_fields = ['key', 'description']
    readonly_fields = ['key']
    list_per_page = 20  # 配置数据较少

    # Unfold specific configurations
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    # 显示完整结果计数
    show_full_result_count = True

    def get_value_preview(self, obj):
        """显示配置值的预览（截断长文本，遮罩敏感信息）"""
        # 敏感配置列表
        sensitive_keys = [
            'hieds_secret', 'idaas_secret', 'welink_client_secret',
            'email_auth_token', 'hieds_account', 'idaas_account'
        ]

        if obj.key in sensitive_keys:
            return self._mask_sensitive_value(obj.value)
        elif len(obj.value) > 50:
            return obj.value[:47] + "..."
        return obj.value
    get_value_preview.short_description = '配置值'

    def _mask_sensitive_value(self, value):
        """遮罩敏感信息"""
        if len(value) <= 4:
            return '*' * len(value)
        return value[:2] + '*' * (len(value) - 4) + value[-2:]

    def get_config_category(self, obj):
        """显示配置分类"""
        categories = {
            'system_config': ['hr_sync_enabled', 'task_auto_creation_enabled', 'task_processing_enabled', 'account_creation_enabled'],
            'hr_sync_config': ['hieds_account', 'hieds_secret', 'hieds_project', 'hieds_enterprise', 'hieds_person_project_id', 'hieds_tenant_id', 'hieds_page_size'],
            'task_config': ['account_creation_max_retries', 'valid_employee_statuses'],
            'idaas_config': ['idaas_account', 'idaas_secret', 'idaas_enterprise_id', 'idaas_domain'],
            'welink_config': ['welink_client_id', 'welink_client_secret'],
            'email_config': ['email_domain', 'email_auth_token']
        }

        for category, keys in categories.items():
            if obj.key in keys:
                return category.replace('_', ' ').title()
        return '其他'

    get_config_category.short_description = '配置分类'
    get_config_category.admin_order_field = 'key'


@admin.register(DepartmentMapping)
class DepartmentMappingAdmin(ModelAdmin):
    list_display = ['idata_departmentcode', 'idaas_departmentcode', 'ou']
    search_fields = ['idata_departmentcode', 'idaas_departmentcode', 'ou']
    list_per_page = 20  # 映射数据较少

    # Unfold specific configurations
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    # 显示完整结果计数
    show_full_result_count = True


class AccountCreationLogInline(TabularInline):
    """账号创建日志内联显示"""
    model = AccountCreationLog
    readonly_fields = ['execution_attempt', 'error_message', 'error_details', 'execution_context', 'created_at']
    can_delete = False
    extra = 0
    max_num = 0
    ordering = ['execution_attempt']
    verbose_name = '执行日志'
    verbose_name_plural = '执行日志'

    # Unfold specific configurations
    compressed_fields = True


@admin.register(AccountCreationTask)
class AccountCreationTaskAdmin(ModelAdmin):
    list_display = [
        'task_id', 'person', 'account_type', 'status',
        'get_retry_count_display', 'created_at', 'completed_at'
    ]
    inlines = [AccountCreationLogInline]
    list_filter = [
        'status',
        'account_type',
        ('created_at', RangeDateTimeFilter),
        ('completed_at', RangeDateTimeFilter),
    ]
    search_fields = ['task_id', 'person__employee_number', 'person__full_name']
    readonly_fields = [
        'task_id', 'person', 'account_type', 'result_data',
        'depends_on_task', 'created_at', 'updated_at', 'completed_at'
    ]
    raw_id_fields = ['person', 'depends_on_task']
    list_per_page = 25  # 任务数据分页

    # Unfold specific configurations
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True
    list_filter_submit = True
    list_filter_sheet = False

    # 显示完整结果计数
    show_full_result_count = True

    def get_queryset(self, request):
        """优化查询，预计算重试次数并预加载日志数据避免 N+1 查询"""
        queryset = super().get_queryset(request)
        # 使用 annotate 预计算重试次数
        from django.db.models import Count
        return queryset.annotate(
            retry_count_annotated=Count('error_logs')
        ).select_related('person').prefetch_related('error_logs')

    def get_retry_count_display(self, obj):
        """显示预计算的重试次数"""
        return getattr(obj, 'retry_count_annotated', 0)
    get_retry_count_display.short_description = '重试次数'
    get_retry_count_display.short_description = '重试次数'
    get_retry_count_display.admin_order_field = 'retry_count_annotated'

    def retry_failed_tasks(self, request, queryset):
        """重试失败的任务并立即执行账号创建"""
        service = AccountCreationService()
        success_count = 0
        failed_count = 0
        skipped_count = 0
        errors = []

        for task in queryset:
            try:
                if task.status != 'failed':
                    skipped_count += 1
                    continue

                # 标记为处理中
                task.mark_processing()

                # 获取部门代码
                department_code = self._get_department_code(task.person)

                if not department_code:
                    raise Exception("无法获取部门代码，跳过账号创建")

                # 执行账号创建
                result = service.create_account(task.person, task.account_type, department_code)

                # 标记为完成
                task.mark_completed(result)

                # 更新 HrPersonAccount 记录
                self._update_person_account(task, result)

                success_count += 1

            except Exception as e:
                # 标记为失败并记录错误日志
                task.mark_failed(str(e))
                errors.append(f"任务 {task.task_id}: {str(e)}")
                failed_count += 1

        # 发送彩色反馈消息
        self._send_retry_feedback_messages(request, success_count, failed_count, skipped_count, errors)

    def _get_department_code(self, person):
        """获取人员的部门代码"""
        if person.person_dept and isinstance(person.person_dept, list) and person.person_dept:
            # 假设部门信息在 person_dept 的第一个元素
            dept_info = person.person_dept[0] if isinstance(person.person_dept, list) else person.person_dept
            if isinstance(dept_info, dict):
                return dept_info.get('department_code') or dept_info.get('dept_code')

        # 尝试从其他字段获取部门代码
        return getattr(person, 'department_code', None)

    def _update_person_account(self, task, result):
        """更新人员账号记录"""
        account_data = {
            'person': task.person,
            'account_type': task.account_type,
            'is_created': True,
        }

        # 根据账号类型设置账号标识
        if task.account_type == 'email':
            account_data['account_identifier'] = result.get('account_identifier') or result.get('email')
        elif task.account_type in ['idaas', 'welink']:
            account_data['account_identifier'] = result.get('account_identifier')

        # 更新或创建账号记录
        account, created = HrPersonAccount.objects.get_or_create(
            person=task.person,
            account_type=task.account_type,
            defaults=account_data
        )

        if not created:
            # 更新现有记录
            for key, value in account_data.items():
                setattr(account, key, value)
            account.save()

    def _send_retry_feedback_messages(self, request, success_count, failed_count, skipped_count, errors):
        """发送重试操作的彩色反馈消息"""
        if success_count > 0:
            self.message_user(
                request,
                f"成功重试并创建了 {success_count} 个账号",
                messages.SUCCESS
            )

        if failed_count > 0:
            error_msg = f"重试失败 {failed_count} 个任务"
            if len(errors) <= 3:
                error_msg += f": {', '.join(errors)}"
            self.message_user(request, error_msg, messages.ERROR)

        if skipped_count > 0:
            self.message_user(
                request,
                f"跳过 {skipped_count} 个任务（不符合重试条件）",
                messages.WARNING
            )

    retry_failed_tasks.short_description = '重试'

    # 批量状态修改操作
    def bulk_set_pending(self, request, queryset):
        """批量将选中的任务设为待处理状态"""
        updated = queryset.update(status='pending')
        self.message_user(
            request,
            f"成功将 {updated} 个任务设为待处理状态",
            messages.SUCCESS
        )


    # 设置操作描述和权限
    bulk_set_pending.short_description = '设置为待处理'
    bulk_set_pending.allowed_permissions = ('change',)
    actions = [retry_failed_tasks, bulk_set_pending]


@admin.register(AccountCreationLog)
class AccountCreationLogAdmin(ModelAdmin):
    list_display = [
        'task', 'execution_attempt', 'get_error_preview', 'created_at'
    ]
    list_filter = [
        ('created_at', RangeDateTimeFilter),
        ('execution_attempt', RangeNumericFilter),
    ]
    search_fields = ['task__task_id', 'error_message']
    readonly_fields = ['task', 'execution_attempt', 'created_at']
    raw_id_fields = ['task']
    list_per_page = 25  # 日志数据分页

    # Unfold specific configurations
    compressed_fields = True
    warn_unsaved_form = False  # 日志通常只读
    list_fullwidth = True
    list_filter_sheet = False

    # 显示完整结果计数
    show_full_result_count = True

    def get_queryset(self, request):
        """优化查询，避免 N+1 查询"""
        return super().get_queryset(request).select_related('task')

    def get_error_preview(self, obj):
        """显示错误信息的预览"""
        if len(obj.error_message) > 100:
            return obj.error_message[:97] + "..."
        return obj.error_message
    get_error_preview.short_description = '错误信息'