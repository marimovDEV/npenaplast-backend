from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from accounts.permissions import IsFinanceManager
from .models import CostCenter, Budget, TrueCostEstimation
from .serializers import CostCenterSerializer, BudgetSerializer, TrueCostEstimationSerializer

class CostCenterViewSet(viewsets.ModelViewSet):
    queryset = CostCenter.objects.all()
    serializer_class = CostCenterSerializer
    permission_classes = [IsFinanceManager]

class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer
    permission_classes = [IsFinanceManager]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cost_center', 'fiscal_period', 'status']

class TrueCostEstimationViewSet(viewsets.ModelViewSet):
    queryset = TrueCostEstimation.objects.all()
    serializer_class = TrueCostEstimationSerializer
    permission_classes = [IsFinanceManager]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['production_type', 'reference_id']
