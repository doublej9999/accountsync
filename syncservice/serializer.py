from rest_framework import serializers

from syncservice.models import HrPerson, SyncConfig


class HrPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = HrPerson
        fields = '__all__'


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