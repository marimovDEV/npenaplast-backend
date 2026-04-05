from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CashboxViewSet, ExpenseCategoryViewSet, 
    FinancialTransactionViewSet, ClientBalanceViewSet,
    InternalTransferViewSet, FinanceAnalyticsView, FinanceExportView
)

router = DefaultRouter()
router.register(r'cashboxes', CashboxViewSet)
router.register(r'categories', ExpenseCategoryViewSet)
router.register(r'transactions', FinancialTransactionViewSet)
router.register(r'transfers', InternalTransferViewSet)
router.register(r'client-balances', ClientBalanceViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('analytics/', FinanceAnalyticsView.as_view(), name='finance-analytics'),
    path('export/', FinanceExportView.as_view(), name='finance-export'),
]
