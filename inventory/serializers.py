from rest_framework import serializers
from .models import Inventory
from warehouse_v2.serializers import MaterialSerializer, WarehouseSerializer

class InventorySerializer(serializers.ModelSerializer):
    product_details = MaterialSerializer(source='product', read_only=True)
    warehouse_details = WarehouseSerializer(source='warehouse', read_only=True)

    class Meta:
        model = Inventory
        fields = ('id', 'product', 'warehouse', 'quantity', 'batch_number', 'supplier', 'created_at', 'product_details', 'warehouse_details')
