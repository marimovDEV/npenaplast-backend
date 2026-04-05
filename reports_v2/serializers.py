from rest_framework import serializers
from .models import ReportHistory

class ReportHistorySerializer(serializers.ModelSerializer):
    created_by_name = serializers.ReadOnlyField(source='created_by.username')
    
    class Meta:
        model = ReportHistory
        fields = [
            'id', 'name', 'report_type', 'period', 'file_format', 
            'file_size', 'status', 'created_at', 'created_by_name', 'file_path'
        ]
