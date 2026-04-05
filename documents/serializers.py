from rest_framework import serializers
from .models import Document, DocumentItem, DocumentDelivery
from warehouse_v2.serializers import MaterialSerializer

class DocumentDeliverySerializer(serializers.ModelSerializer):
    courier_name = serializers.CharField(source='courier.username', read_only=True)
    
    class Meta:
        model = DocumentDelivery
        fields = ('id', 'courier', 'courier_name', 'pickup_at', 'delivered_at')

class DocumentItemSerializer(serializers.ModelSerializer):
    product_details = MaterialSerializer(source='product', read_only=True)
    
    class Meta:
        model = DocumentItem
        fields = ('id', 'product', 'quantity', 'batch_number', 'product_details')

class DocumentSerializer(serializers.ModelSerializer):
    items = DocumentItemSerializer(many=True, required=False)
    delivery = DocumentDeliverySerializer(read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    from_entity_name = serializers.ReadOnlyField()
    to_entity_name = serializers.ReadOnlyField()
    type_label = serializers.CharField(source='get_type_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Document
        fields = (
            'id', 'number', 'type', 'type_label', 'status', 'status_label',
            'from_warehouse', 'to_warehouse', 'client', 'from_entity_name', 'to_entity_name',
            'invoice_date', 'supplier_name', 'total_amount', 'currency', 'exchange_rate',
            'created_by', 'created_by_name', 'deadline', 'qr_code', 'created_at', 'items', 'delivery'
        )
        read_only_fields = ('qr_code', 'created_at')

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        document = super().create(validated_data)
        for item_data in items_data:
            DocumentItem.objects.create(
                document=document,
                **item_data
            )
        return document
