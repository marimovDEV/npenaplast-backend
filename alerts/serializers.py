from rest_framework import serializers
from .models import AlertRule, Alert

class AlertRuleSerializer(serializers.ModelSerializer):
    trigger_type_display = serializers.CharField(source='get_trigger_type_display', read_only=True)

    class Meta:
        model = AlertRule
        fields = '__all__'

class AlertSerializer(serializers.ModelSerializer):
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.full_name', read_only=True)

    class Meta:
        model = Alert
        fields = [
            'id', 'rule', 'title', 'message', 'severity', 'severity_display',
            'is_resolved', 'resolved_by', 'resolved_by_name', 'created_at'
        ]
