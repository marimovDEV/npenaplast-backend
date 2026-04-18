from django.db.models import Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Supplier, Material, RawMaterialBatch, Warehouse, Stock, WarehouseTransfer
from .serializers import (
    SupplierSerializer, MaterialSerializer, RawMaterialBatchSerializer,
    WarehouseSerializer, StockSerializer, WarehouseTransferSerializer
)
from accounts.permissions import IsAdmin, IsWarehouseOperator, get_user_role_name

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAdmin]

class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # All authenticated users can READ materials
            return [permissions.IsAuthenticated()]
        # Only warehouse operators can create/update/delete
        return [IsWarehouseOperator()]

class RawMaterialBatchViewSet(viewsets.ModelViewSet):
    serializer_class = RawMaterialBatchSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [IsWarehouseOperator()]

    def get_queryset(self):
        user = self.request.user
        if get_user_role_name(user) in ['Bosh Admin', 'Admin', 'SUPERADMIN', 'ADMIN'] or user.is_superuser:
            return RawMaterialBatch.objects.all()
        # For operators, show batches they created or those in their assigned warehouses
        return RawMaterialBatch.objects.filter(
            Q(responsible_user=user) | 
            Q(material__stock__warehouse__in=user.assigned_warehouses.all())
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(responsible_user=self.request.user)

    @action(detail=False, methods=['get'], url_path='by-qr/(?P<qr_code>[^/.]+)')
    def by_qr(self, request, qr_code=None):
        try:
            batch = RawMaterialBatch.objects.get(qr_code=qr_code)
            serializer = self.get_serializer(batch)
            return Response(serializer.data)
        except RawMaterialBatch.DoesNotExist:
            return Response({'error': 'Partiya topilmadi'}, status=status.HTTP_404_NOT_FOUND)

class WarehouseViewSet(viewsets.ModelViewSet):
    serializer_class = WarehouseSerializer
    filterset_fields = ['name']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # All authenticated users can see warehouses
            return [permissions.IsAuthenticated()]
        # Only warehouse operators can create/update/delete
        return [IsWarehouseOperator()]

    def get_queryset(self):
        user = self.request.user
        if get_user_role_name(user) in ['Bosh Admin', 'Admin', 'SUPERADMIN', 'ADMIN'] or user.is_superuser:
            return Warehouse.objects.all()
        return user.assigned_warehouses.all()

class StockViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockSerializer
    filterset_fields = {
        'warehouse': ['exact'],
        'warehouse_id': ['exact'],
        'material': ['exact'],
        'material_id': ['exact'],
        'material__name': ['icontains', 'exact'],
    }

    def get_permissions(self):
        # All authenticated users can view stock levels
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if get_user_role_name(user) in ['Bosh Admin', 'Admin', 'SUPERADMIN', 'ADMIN'] or user.is_superuser:
            return Stock.objects.all().select_related('warehouse', 'material')
        return Stock.objects.filter(warehouse__in=user.assigned_warehouses.all()).select_related('warehouse', 'material')

class WarehouseTransferViewSet(viewsets.ModelViewSet):
    serializer_class = WarehouseTransferSerializer
    permission_classes = [IsWarehouseOperator]

    def get_queryset(self):
        user = self.request.user
        if get_user_role_name(user) in ['Bosh Admin', 'Admin', 'SUPERADMIN', 'ADMIN'] or user.is_superuser:
            return WarehouseTransfer.objects.all()
        return WarehouseTransfer.objects.filter(
            Q(from_warehouse__in=user.assigned_warehouses.all()) |
            Q(to_warehouse__in=user.assigned_warehouses.all())
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(approved_by=self.request.user)
