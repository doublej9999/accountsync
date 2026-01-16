from rest_framework import serializers

from syncservice.models import HrPerson, SyncConfig, HrPersonAccount


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


class ManualSyncSerializer(serializers.Serializer):
    """手动同步序列化器"""
    force_full_sync = serializers.BooleanField(default=False, required=False)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100, required=False)