from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes

from syncservice.models import HrPerson, SyncConfig, HrPersonAccount, DepartmentMapping, AccountCreationTask, AccountCreationLog, AccountCreationRequest, AccountCreationRequestItem


class HrPersonAccountSerializer(serializers.ModelSerializer):
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)

    class Meta:
        model = HrPersonAccount
        fields = '__all__'


class HrPersonSerializer(serializers.ModelSerializer):
    accounts = HrPersonAccountSerializer(many=True, read_only=True)

    class Meta:
        model = HrPerson
        fields = '__all__'


class HrPersonDetailSerializer(serializers.ModelSerializer):
    """人员详细信息序列化器，包含账号信息"""
    accounts = HrPersonAccountSerializer(many=True, read_only=True)
    account_status = serializers.SerializerMethodField()

    class Meta:
        model = HrPerson
        fields = '__all__'

    def get_account_status(self, obj):
        """获取账号创建状态统计"""
        accounts = obj.accounts.all()
        total = accounts.count()
        created = accounts.filter(is_created=True).count()

        return {
            'total': total,
            'created': created,
            'pending': total - created,
            'completion_rate': f"{(created/total*100):.1f}%" if total > 0 else "0%"
        }


class SyncConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncConfig
        fields = '__all__'


class SyncStatusSerializer(serializers.Serializer):
    """同步状态序列化器"""
    last_sync_time = serializers.DateTimeField(read_only=True)
    total_persons = serializers.IntegerField(read_only=True)
    last_sync_status = serializers.CharField(read_only=True)
    next_sync_time = serializers.DateTimeField(read_only=True)

class DepartmentMappingSerializer(serializers.ModelSerializer):
    """部门映射序列化器"""
    class Meta:
        model = DepartmentMapping
        fields = '__all__'


class AccountCreationRequestSerializer(serializers.Serializer):
    """账号创建请求序列化器"""
    originSystem = serializers.CharField(required=True)
    businessKey = serializers.CharField(required=True)
    accountType = serializers.CharField(required=True)
    employeeType = serializers.CharField(required=True)
    systemList = serializers.ListField(
        child=serializers.ChoiceField(choices=['idaas', 'welink', 'email']),
        required=True,
        min_length=1
    )
    userList = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        min_length=1
    )

    def validate_systemList(self, value):
        """验证 systemList 包含有效的账号类型"""
        valid_types = ['idaas', 'welink', 'email']
        for item in value:
            if item not in valid_types:
                raise serializers.ValidationError(f"无效的账号类型: {item}")
        return value


class UserCreationDataSerializer(serializers.Serializer):
    """用户创建数据序列化器"""
    employeeNumber = serializers.CharField(required=True)
    employeeName = serializers.CharField(required=True)
    departmentCode = serializers.CharField(required=True)
    phoneNumber = serializers.CharField(required=True)
    partnerCompany = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=True)


class AccountCreationLogSerializer(serializers.ModelSerializer):
    """账号创建日志序列化器"""
    task_info = serializers.SerializerMethodField()

    class Meta:
        model = AccountCreationLog
        fields = '__all__'

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_task_info(self, obj):
        return {
            'task_id': obj.task.task_id,
            'person': obj.task.person.employee_number,
            'account_type': obj.task.account_type
        }


class AccountCreationTaskSerializer(serializers.ModelSerializer):
    """账号创建任务序列化器"""
    person_info = serializers.SerializerMethodField()
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    retry_count = serializers.SerializerMethodField()
    error_logs = serializers.SerializerMethodField()

    class Meta:
        model = AccountCreationTask
        fields = '__all__'
        read_only_fields = ['task_id', 'result_data', 'created_at', 'updated_at', 'completed_at']

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_person_info(self, obj):
        return {
            'employee_number': obj.person.employee_number,
            'full_name': obj.person.full_name,
            'email': obj.person.email_address,
            'department': obj.person.person_dept if obj.person.person_dept else {}
        }

    @extend_schema_field(OpenApiTypes.INT)
    def get_retry_count(self, obj):
        return obj.retry_count

    @extend_schema_field(AccountCreationLogSerializer(many=True))
    def get_error_logs(self, obj):
        logs = obj.error_logs.all()
        return AccountCreationLogSerializer(logs, many=True).data


class TaskExecutionSerializer(serializers.Serializer):
    """任务执行序列化器"""
    mode = serializers.ChoiceField(choices=['dry_run', 'run'], default='dry_run')

    # HR同步参数
    force_full_sync = serializers.BooleanField(default=False, required=False)

    # 任务创建参数
    employee_status = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )

    # 任务处理参数
    max_tasks = serializers.IntegerField(default=50, min_value=1, required=False)


class AccountCreationRequestSerializer(serializers.ModelSerializer):
    """账号创建请求序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    # 字段别名，支持驼峰命名
    originSystem = serializers.CharField(source='origin_system', required=True)
    businessKey = serializers.CharField(source='business_key', required=True)
    accountType = serializers.CharField(source='account_type', required=True)
    employeeType = serializers.CharField(source='employee_type', required=True)
    systemList = serializers.ListField(
        child=serializers.ChoiceField(choices=['idaas', 'welink', 'email']),
        source='system_list',
        required=True
    )
    userList = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        write_only=True
    )

    class Meta:
        model = AccountCreationRequest
        fields = ['request_id', 'originSystem', 'businessKey',
                  'accountType', 'employeeType',
                  'systemList', 'userList', 'status', 'status_display',
                  'total_users', 'processed_users', 'error_summary',
                  'created_at', 'updated_at', 'completed_at']
        read_only_fields = ['request_id', 'status', 'total_users', 'processed_users',
                            'error_summary', 'created_at', 'updated_at', 'completed_at']


class AccountCreationRequestItemSerializer(serializers.ModelSerializer):
    """账号创建请求项序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    hr_person_info = serializers.SerializerMethodField()

    class Meta:
        model = AccountCreationRequestItem
        fields = ['id', 'employee_number', 'employee_name', 'department_code',
                  'phone_number', 'partner_company', 'country', 'status',
                  'status_display', 'hr_person_info', 'error_message',
                  'created_at', 'updated_at']

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_hr_person_info(self, obj):
        if obj.hr_person:
            return {
                'employee_number': obj.hr_person.employee_number,
                'full_name': obj.hr_person.full_name,
                'email': obj.hr_person.email_address
            }
        return None


class AccountCreationRequestDetailSerializer(serializers.ModelSerializer):
    """账号创建请求详情序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items = AccountCreationRequestItemSerializer(many=True, read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = AccountCreationRequest
        fields = ['request_id', 'origin_system', 'business_key', 'account_type',
                  'employee_type', 'system_list', 'status', 'status_display',
                  'total_users', 'processed_users', 'progress', 'error_summary',
                  'created_at', 'updated_at', 'completed_at', 'items']
        read_only_fields = ['request_id', 'status', 'total_users', 'processed_users',
                            'error_summary', 'created_at', 'updated_at', 'completed_at']

    @extend_schema_field(OpenApiTypes.STR)
    def get_progress(self, obj):
        if obj.total_users == 0:
            return "0%"
        percentage = (obj.processed_users / obj.total_users) * 100
        return f"{percentage:.1f}%"