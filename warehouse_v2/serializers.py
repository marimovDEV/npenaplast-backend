from rest_framework import serializers
from .models import Supplier, Material, RawMaterialBatch, Warehouse, Stock, WarehouseTransfer

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

class MaterialSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = Material
        fields = ['id', 'name', 'sku', 'category', 'category_display', 'unit', 'price', 'description']

class RawMaterialBatchSerializer(serializers.ModelSerializer):
    supplier_name = serializers.ReadOnlyField(source='supplier.name')
    material_name = serializers.ReadOnlyField(source='material.name')
    responsible_user_name = serializers.ReadOnlyField(source='responsible_user.full_name')

    class Meta:
        model = RawMaterialBatch
        fields = '__all__'

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = '__all__'

class StockSerializer(serializers.ModelSerializer):
    material_name = serializers.ReadOnlyField(source='material.name')
    material_price = serializers.ReadOnlyField(source='material.price')
    material_unit = serializers.ReadOnlyField(source='material.unit')
    warehouse_name = serializers.ReadOnlyField(source='warehouse.name')

    class Meta:
        model = Stock
        fields = '__all__'

class WarehouseTransferSerializer(serializers.ModelSerializer):
    material_name = serializers.ReadOnlyField(source='material.name')
    from_warehouse_name = serializers.ReadOnlyField(source='from_warehouse.name')
    to_warehouse_name = serializers.ReadOnlyField(source='to_warehouse.name')

    class Meta:
        model = WarehouseTransfer
        fields = '__all__'
