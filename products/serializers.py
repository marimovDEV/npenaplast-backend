from rest_framework import serializers
from .models import Product, ProductionTask

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class ProductionTaskSerializer(serializers.ModelSerializer):
    responsible_person_name = serializers.CharField(source='responsible_person.username', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = ProductionTask
        fields = '__all__'
