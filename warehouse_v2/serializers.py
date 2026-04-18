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
    
    available_quantity = serializers.SerializerMethodField()
    reserved_quantity = serializers.SerializerMethodField()
    total_value = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = '__all__'

    def get_reserved_quantity(self, obj):
        # Heuristic: Sum reserved quantities from batches of this material
        # Note: In multi-warehouse, we'd filter by batch location, but here we assume Sklad 1
        from .models import RawMaterialBatch
        return RawMaterialBatch.objects.filter(
            material=obj.material, 
            status__in=['IN_STOCK', 'RESERVED']
        ).aggregate(s=serializers.models.Sum('reserved_quantity'))['s'] or 0

    def get_available_quantity(self, obj):
        reserved = self.get_reserved_quantity(obj)
        return max(0, obj.quantity - reserved)

    def get_total_value(self, obj):
        return float(obj.quantity) * float(obj.material.price)

    def get_status(self, obj):
        if obj.quantity <= obj.min_level:
            return 'CRITICAL'
        if obj.quantity <= obj.min_level * 1.5:
            return 'LOW'
        return 'OK'

class WarehouseTransferSerializer(serializers.ModelSerializer):
    material_name = serializers.ReadOnlyField(source='material.name')
    from_warehouse_name = serializers.ReadOnlyField(source='from_warehouse.name')
    to_warehouse_name = serializers.ReadOnlyField(source='to_warehouse.name')

    class Meta:
        model = WarehouseTransfer
        fields = '__all__'
