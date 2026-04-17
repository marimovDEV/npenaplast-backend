from rest_framework import serializers
from .models import LegalDocument, ComplianceRule, ComplianceViolation

class LegalDocumentSerializer(serializers.ModelSerializer):
    signed_by_name = serializers.CharField(source='signed_by.full_name', read_only=True)
    doc_type_display = serializers.CharField(source='get_doc_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = LegalDocument
        fields = [
            'id', 'doc_number', 'title', 'doc_type', 'doc_type_display',
            'status', 'status_display', 'file', 'digital_signature',
            'signed_by', 'signed_by_name', 'signed_at', 'created_at', 'updated_at'
        ]

class ComplianceRuleSerializer(serializers.ModelSerializer):
    rule_type_display = serializers.CharField(source='get_rule_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)

    class Meta:
        model = ComplianceRule
        fields = '__all__'

class ComplianceViolationSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    severity = serializers.CharField(source='rule.severity', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.full_name', read_only=True)

    class Meta:
        model = ComplianceViolation
        fields = [
            'id', 'rule', 'rule_name', 'severity', 'description', 'context_data',
            'is_resolved', 'resolved_by', 'resolved_by_name', 'resolution_note', 'created_at'
        ]
