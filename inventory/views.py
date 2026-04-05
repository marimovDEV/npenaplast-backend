from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import InventoryBatch, InventoryMovement
from .serializers import InventoryBatchSerializer, InventoryMovementSerializer

class InventoryBatchViewSet(viewsets.ModelViewSet):
    queryset = InventoryBatch.objects.all().order_by('-created_at')
    serializer_class = InventoryBatchSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'location', 'status', 'source']
    search_fields = ['batch_number', 'product__name']
    ordering_fields = ['created_at', 'current_weight']

    def perform_destroy(self, instance):
        # Soft delete
        instance.is_deleted = True
        instance.save()

class InventoryMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InventoryMovement.objects.all().order_by('-timestamp')
    serializer_class = InventoryMovementSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['batch', 'type', 'from_location', 'to_location']
    search_fields = ['reference', 'batch__batch_number']
