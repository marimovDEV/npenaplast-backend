from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomerViewSet, InvoiceViewSet, SaleItemViewSet,
    ContractViewSet, NotificationLogViewSet,
    SalesKPIView, DebtorsView, SalesExportView
)

router = DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'invoices', InvoiceViewSet)
router.register(r'items', SaleItemViewSet)
router.register(r'contracts', ContractViewSet)
router.register(r'notifications', NotificationLogViewSet, basename='notifications')

urlpatterns = [
    path('', include(router.urls)),
    path('kpi/', SalesKPIView.as_view(), name='sales-kpi'),
    path('debtors/', DebtorsView.as_view(), name='sales-debtors'),
    path('export/', SalesExportView.as_view(), name='sales-export'),
]
