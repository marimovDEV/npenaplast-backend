from rest_framework import serializers
from .models import CostCenter, Budget, TrueCostEstimation

class CostCenterSerializer(serializers.ModelSerializer):
    manager_name = serializers.CharField(source='manager.full_name', read_only=True)

    class Meta:
        model = CostCenter
        fields = '__all__'

class BudgetSerializer(serializers.ModelSerializer):
    cost_center_name = serializers.CharField(source='cost_center.name', read_only=True)
    account_code = serializers.CharField(source='account.code', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    variance = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    used_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = Budget
        fields = [
            'id', 'name', 'fiscal_period', 'cost_center', 'cost_center_name',
            'account', 'account_code', 'account_name', 'planned_amount',
            'actual_amount', 'status', 'created_at', 'variance', 'used_percentage'
        ]

class TrueCostEstimationSerializer(serializers.ModelSerializer):
    total_cost = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = TrueCostEstimation
        fields = [
            'id', 'production_type', 'reference_id', 'material_cost',
            'labor_cost', 'energy_cost', 'overhead_cost', 'total_cost', 'created_at'
        ]
