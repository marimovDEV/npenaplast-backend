from rest_framework import serializers
from .models import InventoryBatch, InventoryMovement

class InventoryBatchSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    warehouse_name = serializers.ReadOnlyField(source='location.name')
    
    class Meta:
        model = InventoryBatch
        fields = [
            'id', 'batch_number', 'product', 'product_name', 'source',
            'initial_weight', 'current_weight', 'location', 'warehouse_name',
            'status', 'qr_id', 'created_at', 'updated_at'
        ]

class InventoryMovementSerializer(serializers.ModelSerializer):
    batch_number = serializers.ReadOnlyField(source='batch.batch_number')
    performer_name = serializers.ReadOnlyField(source='performed_by.name')
    
    class Meta:
        model = InventoryMovement
        fields = [
            'id', 'batch', 'batch_number', 'from_location', 'to_location',
            'quantity', 'type', 'reference', 'timestamp', 'performer_name', 'notes'
        ]
