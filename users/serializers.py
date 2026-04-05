from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email', 'role', 'name', 'first_name', 'last_name', 'assigned_warehouses')
        read_only_fields = ('id',)

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        assigned_warehouses = validated_data.pop('assigned_warehouses', [])
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        if assigned_warehouses:
            user.assigned_warehouses.set(assigned_warehouses)
        return user
