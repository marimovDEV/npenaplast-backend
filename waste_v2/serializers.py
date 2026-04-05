from rest_framework import serializers
from .models import WasteTask, WasteCategory

class WasteCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WasteCategory
        fields = '__all__'

class WasteTaskSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    operator_name = serializers.ReadOnlyField(source='operator.first_name')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    dept_display = serializers.CharField(source='get_source_department_display', read_only=True)

    class Meta:
        model = WasteTask
        fields = '__all__'
