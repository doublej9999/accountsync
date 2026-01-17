from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    RangeDateFilter,
    RangeDateTimeFilter,
    RangeNumericFilter,
    SingleNumericFilter
)

from syncservice.models import (
    HrPerson, HrPersonAccount, SyncConfig, DepartmentMapping,
    AccountCreationTask, AccountCreationLog
)


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
    list_per_page = 50  # 人员数据分页

    # Unfold specific configurations
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True
    list_filter_submit = True


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

    def get_queryset(self, request):
        """优化查询，避免 N+1 查询"""
        return super().get_queryset(request).select_related('person')


@admin.register(SyncConfig)
class SyncConfigAdmin(ModelAdmin):
    list_display = ['key', 'get_value_preview', 'description']
    search_fields = ['key', 'description']
    readonly_fields = ['key']
    list_per_page = 20  # 配置数据较少

    # Unfold specific configurations
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    def get_value_preview(self, obj):
        """显示配置值的预览（截断长文本）"""
        if len(obj.value) > 50:
            return obj.value[:47] + "..."
        return obj.value
    get_value_preview.short_description = '配置值'


@admin.register(DepartmentMapping)
class DepartmentMappingAdmin(ModelAdmin):
    list_display = ['idata_departmentcode', 'idaas_departmentcode', 'ou']
    search_fields = ['idata_departmentcode', 'idaas_departmentcode', 'ou']
    list_per_page = 20  # 映射数据较少

    # Unfold specific configurations
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True


@admin.register(AccountCreationTask)
class AccountCreationTaskAdmin(ModelAdmin):
    list_display = [
        'task_id', 'person', 'account_type', 'status',
        'get_retry_count_display', 'created_at', 'completed_at'
    ]
    list_filter = [
        'status',
        'account_type',
        ('created_at', RangeDateTimeFilter),
        ('completed_at', RangeDateTimeFilter),
    ]
    search_fields = ['task_id', 'person__employee_number', 'person__full_name']
    readonly_fields = ['task_id', 'created_at', 'updated_at', 'completed_at']
    raw_id_fields = ['person', 'depends_on_task']
    list_per_page = 25  # 任务数据分页

    # Unfold specific configurations
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True
    list_filter_submit = True
    list_filter_sheet = False

    def get_queryset(self, request):
        """优化查询，预计算重试次数避免 N+1 查询"""
        queryset = super().get_queryset(request)
        # 使用 annotate 预计算重试次数
        from django.db.models import Count
        return queryset.annotate(
            retry_count_annotated=Count('error_logs')
        ).select_related('person')

    def get_retry_count_display(self, obj):
        """显示预计算的重试次数"""
        return getattr(obj, 'retry_count_annotated', 0)
    get_retry_count_display.short_description = '重试次数'
    get_retry_count_display.admin_order_field = 'retry_count_annotated'


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

    def get_queryset(self, request):
        """优化查询，避免 N+1 查询"""
        return super().get_queryset(request).select_related('task')

    def get_error_preview(self, obj):
        """显示错误信息的预览"""
        if len(obj.error_message) > 100:
            return obj.error_message[:97] + "..."
        return obj.error_message
    get_error_preview.short_description = '错误信息'