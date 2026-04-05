from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Product, ProductionTask
from .serializers import ProductSerializer, ProductionTaskSerializer
from .services import advance_task_stage, complete_production_task

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class ProductionTaskViewSet(viewsets.ModelViewSet):
    queryset = ProductionTask.objects.all()
    serializer_class = ProductionTaskSerializer
    filterset_fields = ('stage', 'is_completed')

    @action(detail=True, methods=['patch'])
    def advance(self, request, pk=None):
        task = self.get_object()
        next_stage = request.data.get('stage')
        if not next_stage:
            return Response({'error': 'Stage is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        advance_task_stage(task, next_stage, user=request.user)
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        complete_production_task(task, user=request.user)
        return Response(self.get_serializer(task).data)
