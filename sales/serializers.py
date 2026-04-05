from rest_framework import serializers
from .models import Client, SalesOrder, SalesOrderItem
from products.serializers import ProductSerializer

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'

class SalesOrderItemSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)

    class Meta:
        model = SalesOrderItem
        fields = ('id', 'product', 'quantity', 'price', 'product_details')

class SalesOrderSerializer(serializers.ModelSerializer):
    items = SalesOrderItemSerializer(many=True, required=False)
    client_details = ClientSerializer(source='client', read_only=True)

    class Meta:
        model = SalesOrder
        fields = ('id', 'client', 'status', 'created_at', 'items', 'client_details')

    def create(self, validated_data):
        items_data = self.context['request'].data.get('items', [])
        order = SalesOrder.objects.create(**validated_data)
        for item_data in items_data:
            SalesOrderItem.objects.create(
                order=order,
                product_id=item_data.get('product'),
                quantity=item_data.get('quantity'),
                price=item_data.get('price')
            )
        return order
