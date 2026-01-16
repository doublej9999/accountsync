from datetime import timedelta

import django_filters
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from syncservice.models import HrPerson, SyncConfig, HrPersonAccount
from syncservice.serializer import (
    HrPersonSerializer, HrPersonDetailSerializer, HrPersonAccountSerializer,
    SyncConfigSerializer, SyncStatusSerializer, ManualSyncSerializer
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
        from syncservice.management.commands.sync_hr_persons import Command

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



