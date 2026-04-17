from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CostCenterViewSet, BudgetViewSet, TrueCostEstimationViewSet

router = DefaultRouter()
router.register(r'cost-centers', CostCenterViewSet)
router.register(r'budgets', BudgetViewSet)
router.register(r'true-costs', TrueCostEstimationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
