from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Inventory
from .serializers import InventorySerializer

class InventoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    filterset_fields = ('warehouse', 'product')

    @action(detail=False, methods=['get'])
    def balance(self, request):
        product_id = request.query_params.get('product')
        warehouse_id = request.query_params.get('warehouse')
        queryset = self.queryset
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        total = queryset.aggregate(total=Sum('quantity'))['total'] or 0
        return Response({'total': total})
