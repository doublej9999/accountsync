from datetime import timedelta

import django_filters
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from syncservice.models import HrPerson, SyncConfig, HrPersonAccount, DepartmentMapping, AccountCreationTask
from syncservice.serializer import (
    HrPersonSerializer, HrPersonDetailSerializer, HrPersonAccountSerializer,
    SyncConfigSerializer, SyncStatusSerializer, ManualSyncSerializer,
    DepartmentMappingSerializer, AccountCreationRequestSerializer,
    AccountCreationTaskSerializer, UserCreationDataSerializer,
    AccountCreationLogSerializer
)


class HrPersonFilter(django_filters.FilterSet):
    employee_number = django_filters.CharFilter(lookup_expr="icontains")
    full_name = django_filters.CharFilter(lookup_expr="icontains")
    employee_status = django_filters.CharFilter(lookup_expr="exact")
    person_type = django_filters.CharFilter(lookup_expr="exact")
    creation_date_gte = django_filters.DateTimeFilter(field_name="creation_date", lookup_expr="gte")
    creation_date_lte = django_filters.DateTimeFilter(field_name="creation_date", lookup_expr="lte")

    class Meta:
        model = HrPerson
        fields = ["employee_number", "full_name", "employee_status", "person_type"]


class HrPersonViewSet(ModelViewSet):
    queryset = HrPerson.objects.all()
    serializer_class = HrPersonSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = HrPersonFilter
    search_fields = ["employee_number", "full_name", "english_name", "email_address"]
    ordering_fields = ["creation_date", "last_update_date", "employee_number"]
    ordering = ["-creation_date"]

    @action(detail=False, methods=['get'])
    def sync_status(self, request):
        """获取同步状态"""
        last_sync_time = SyncConfig.get_config('last_sync_time')
        total_persons = HrPerson.objects.count()
        last_sync_status = SyncConfig.get_config('last_sync_status', 'never_synced')

        # 计算下次同步时间（每10分钟）
        next_sync_time = None
        if last_sync_time:
            last_sync = timezone.datetime.fromisoformat(last_sync_time.replace('Z', '+00:00'))
            next_sync_time = last_sync + timedelta(minutes=10)

        data = {
            'last_sync_time': last_sync_time,
            'total_persons': total_persons,
            'last_sync_status': last_sync_status,
            'next_sync_time': next_sync_time
        }

        serializer = SyncStatusSerializer(data)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """重写详情视图，使用详细序列化器"""
        instance = self.get_object()
        serializer = HrPersonDetailSerializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def accounts(self, request, pk=None):
        """获取人员的账号信息"""
        person = self.get_object()
        accounts = person.accounts.all()
        serializer = HrPersonAccountSerializer(accounts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def account_stats(self, request):
        """获取账号创建统计"""
        total_persons = HrPerson.objects.count()
        total_accounts = HrPersonAccount.objects.count()
        created_accounts = HrPersonAccount.objects.filter(is_created=True).count()

        # 按账号类型统计
        stats_by_type = {}
        for account_type, display_name in HrPersonAccount.ACCOUNT_TYPE_CHOICES:
            type_accounts = HrPersonAccount.objects.filter(account_type=account_type)
            type_created = type_accounts.filter(is_created=True).count()
            type_total = type_accounts.count()

            stats_by_type[account_type] = {
                'total': type_total,
                'created': type_created,
                'pending': type_total - type_created,
                'completion_rate': f"{(type_created/type_total*100):.1f}%" if type_total > 0 else "0%"
            }

        data = {
            'total_persons': total_persons,
            'total_accounts': total_accounts,
            'created_accounts': created_accounts,
            'pending_accounts': total_accounts - created_accounts,
            'overall_completion_rate': f"{(created_accounts/total_accounts*100):.1f}%" if total_accounts > 0 else "0%",
            'stats_by_type': stats_by_type
        }

        return Response(data)

    @action(detail=False, methods=['post'])
    def manual_sync(self, request):
        """手动触发同步"""
        from syncservice.management.commands.task.sync_hr_persons import Command

        serializer = ManualSyncSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        force_full_sync = serializer.validated_data.get('force_full_sync', False)
        page_size = serializer.validated_data.get('page_size', 20)

        # 执行同步命令
        try:
            command = Command()
            command.handle(force_full_sync=force_full_sync, page_size=page_size)
            return Response({'message': '同步完成'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HrPersonAccountFilter(django_filters.FilterSet):
    account_type = django_filters.CharFilter(lookup_expr="exact")
    is_created = django_filters.BooleanFilter()
    person__employee_number = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = HrPersonAccount
        fields = ["account_type", "is_created"]


class HrPersonAccountViewSet(ModelViewSet):
    queryset = HrPersonAccount.objects.all()
    serializer_class = HrPersonAccountSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = HrPersonAccountFilter
    search_fields = ["person__employee_number", "person__full_name", "account_identifier"]
    ordering_fields = ["created_at", "updated_at", "account_type"]
    ordering = ["-updated_at"]


class SyncConfigViewSet(ModelViewSet):
    queryset = SyncConfig.objects.all()
    serializer_class = SyncConfigSerializer


class DepartmentMappingViewSet(ModelViewSet):
    queryset = DepartmentMapping.objects.all()
    serializer_class = DepartmentMappingSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['idata_departmentcode', 'idaas_departmentcode']
    search_fields = ['idata_departmentcode', 'idaas_departmentcode', 'ou']
    ordering_fields = ['idata_departmentcode', 'idaas_departmentcode']
    ordering = ['idata_departmentcode']


class AccountCreationViewSet(ModelViewSet):
    queryset = AccountCreationTask.objects.all()
    serializer_class = AccountCreationTaskSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'account_type', 'person__employee_number']
    search_fields = ['task_id', 'person__employee_number', 'person__full_name']
    ordering_fields = ['created_at', 'updated_at', 'status']
    ordering = ['-created_at']

    @action(detail=False, methods=['post'])
    def create_accounts(self, request):
        """批量创建账号"""
        import logging
        logger = logging.getLogger(__name__)

        serializer = AccountCreationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        origin_system = serializer.validated_data['originSystem']
        business_key = serializer.validated_data['businessKey']
        account_type = serializer.validated_data['accountType']
        employee_type = serializer.validated_data['employeeType']
        system_list = serializer.validated_data['systemList']
        user_list = serializer.validated_data['userList']

        # 记录请求日志
        logger.info(f'接收到账号创建请求: {origin_system} - {business_key} - {system_list}')

        created_tasks = []
        errors = []

        for user_data in user_list:
            user_serializer = UserCreationDataSerializer(data=user_data)
            if not user_serializer.is_valid():
                errors.append({
                    'user': user_data,
                    'errors': user_serializer.errors
                })
                continue

            employee_number = user_serializer.validated_data['employeeNumber']
            employee_name = user_serializer.validated_data['employeeName']
            department_code = user_serializer.validated_data['departmentCode']
            phone_number = user_serializer.validated_data['phoneNumber']
            partner_company = user_serializer.validated_data.get('partnerCompany', '')
            country = user_serializer.validated_data['country']

            try:
                # 获取或创建人员记录
                # 注意：person_id 是主键，需要从业务系统中获取或生成
                # 这里暂时使用 employee_number 的数值部分作为 person_id
                # todo 这里的person_id后续需要保持与同步的一致,后面需要重新在获取人员信息，更新person_id
                try:
                    # 尝试从 employee_number 中提取数字部分
                    person_id = employee_number
                except ValueError:
                    # 如果无法提取，使用 hash 的后8位作为较小的整数
                    import hashlib
                    person_id = int(hashlib.md5(employee_number.encode()).hexdigest()[:7], 16)

                person, person_created = HrPerson.objects.get_or_create(
                    employee_number=employee_number,
                    defaults={
                        'person_id': person_id,
                        'full_name': employee_name,
                        'telephone_number1': phone_number,
                        'person_type': account_type,
                        'employee_status': employee_type,
                        'tenant_id': business_key,
                        'created_by': 'account_creation_api',
                        'last_updated_by': 'account_creation_api',
                        'creation_date': timezone.now(),
                        'last_update_date': timezone.now(),
                        'person_dept': [{
                            'department_code': department_code,
                            'partner_company': partner_company,
                            'country': country
                        }]
                    }
                )

                if not person_created:
                    # 更新现有人员信息
                    person.full_name = employee_name
                    person.telephone_number1 = phone_number
                    person.person_type = account_type
                    person.employee_status = employee_type
                    person.last_update_date = timezone.now()
                    person.last_updated_by = 'account_creation_api'
                    if not person.person_dept:
                        person.person_dept = [{
                            'department_code': department_code,
                            'partner_company': partner_company,
                            'country': country
                        }]
                    person.save()

                # 创建账号创建任务
                tasks_for_user = self._create_account_tasks_for_user(
                    person, system_list, origin_system, business_key
                )
                created_tasks.extend(tasks_for_user)

            except Exception as e:
                errors.append({
                    'user': user_data,
                    'error': str(e)
                })

        response_data = {
            'success': len(errors) == 0,
            'created_tasks': len(created_tasks),
            'errors': errors,
            'tasks': AccountCreationTaskSerializer(created_tasks, many=True).data if created_tasks else []
        }

        return Response(response_data, status=status.HTTP_201_CREATED if len(errors) == 0 else status.HTTP_207_MULTI_STATUS)

    def _create_account_tasks_for_user(self, person, system_list, origin_system, business_key):
        """为用户创建账号任务"""
        import logging
        logger = logging.getLogger(__name__)

        created_tasks = []

        # 定义账号创建顺序
        account_order = {
            'idaas': 1,
            'welink': 2,
            'email': 3
        }

        # 按顺序排序系统列表
        sorted_systems = sorted(system_list, key=lambda x: account_order.get(x, 999))

        previous_task = None

        for account_type in sorted_systems:
            # 检查是否已存在进行中的任务
            existing_task = AccountCreationTask.objects.filter(
                person=person,
                account_type=account_type,
                status__in=['pending', 'processing']
            ).first()

            if existing_task:
                logger.info(f'用户 {person.employee_number} 的 {account_type} 账号任务已存在，跳过')
                previous_task = existing_task
                continue

            # 创建新任务
            task = AccountCreationTask.objects.create(
                task_id=f"{business_key}_{person.employee_number}_{account_type}_{timezone.now().timestamp()}",
                person=person,
                account_type=account_type,
                depends_on_task=previous_task
            )

            created_tasks.append(task)
            previous_task = task

            logger.info(f'创建任务: {task.task_id} - {person.employee_number} - {account_type}')

        return created_tasks

    @action(detail=False, methods=['get'])
    def task_stats(self, request):
        """获取任务统计信息"""
        total_tasks = AccountCreationTask.objects.count()
        pending_tasks = AccountCreationTask.objects.filter(status='pending').count()
        processing_tasks = AccountCreationTask.objects.filter(status='processing').count()
        completed_tasks = AccountCreationTask.objects.filter(status='completed').count()
        failed_tasks = AccountCreationTask.objects.filter(status='failed').count()

        # 按账号类型统计
        stats_by_type = {}
        for account_type, display_name in HrPersonAccount.ACCOUNT_TYPE_CHOICES:
            type_tasks = AccountCreationTask.objects.filter(account_type=account_type)
            type_completed = type_tasks.filter(status='completed').count()
            type_total = type_tasks.count()

            stats_by_type[account_type] = {
                'total': type_total,
                'completed': type_completed,
                'pending': type_tasks.filter(status='pending').count(),
                'processing': type_tasks.filter(status='processing').count(),
                'failed': type_tasks.filter(status='failed').count(),
                'completion_rate': f"{(type_completed/type_total*100):.1f}%" if type_total > 0 else "0%"
            }

        data = {
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks,
            'processing_tasks': processing_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'overall_completion_rate': f"{(completed_tasks/total_tasks*100):.1f}%" if total_tasks > 0 else "0%",
            'stats_by_type': stats_by_type
        }

        return Response(data)

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """查看任务的错误日志"""
        task = self.get_object()
        logs = task.error_logs.all().order_by('execution_attempt')

        # 支持分页
        page = self.paginate_queryset(logs)
        serializer = AccountCreationLogSerializer(page, many=True)

        return self.get_paginated_response(serializer.data)



