from rest_framework import serializers
from django.db import transaction
from .models import Supplier, Material, RawMaterialBatch, Warehouse, Stock, WarehouseTransfer
from inventory.services import update_inventory

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

    def create(self, validated_data):
        with transaction.atomic():
            instance = super().create(validated_data)
            # Enterprise Update: Centralized Stock Update via Service
            # Default warehouse for raw materials is Sklad 1
            warehouse, _ = Warehouse.objects.get_or_create(name='Sklad 1 (Xom Ashyo)')
            update_inventory(
                product=instance.material,
                warehouse=warehouse,
                qty=instance.quantity_kg,
                batch_number=instance.batch_number,
                user=instance.responsible_user,
                reference=f"RECEIPT-{instance.invoice_number}"
            )
            return instance

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
        from django.db.models import Sum
        return RawMaterialBatch.objects.filter(
            material=obj.material, 
            status__in=['IN_STOCK', 'RESERVED']
        ).aggregate(s=Sum('reserved_quantity'))['s'] or 0

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

    def create(self, validated_data):
        with transaction.atomic():
            instance = super().create(validated_data)
            # Enterprise Update: Atomic Transfer via Service Layer
            # 1. Decrease from source
            update_inventory(
                product=instance.material,
                warehouse=instance.from_warehouse,
                qty=-instance.quantity,
                user=instance.approved_by,
                reference=f"TRANSFER-OUT-{instance.id}"
            )
            # 2. Increase in destination
            update_inventory(
                product=instance.material,
                warehouse=instance.to_warehouse,
                qty=instance.quantity,
                user=instance.approved_by,
                reference=f"TRANSFER-IN-{instance.id}"
            )
            return instance
