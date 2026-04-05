from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.utils import timezone
from django.db import models

from accounts.permissions import get_user_role_name

from .models import Stock, Material, RawMaterialBatch


def get_visible_stock_queryset(user):
    role_name = get_user_role_name(user)
    queryset = Stock.objects.select_related('warehouse', 'material')
    if user.is_superuser or role_name in ['Bosh Admin', 'Admin', 'SUPERADMIN', 'ADMIN', 'Sotuv menejeri', 'SALES_MANAGER']:
        return queryset
    assigned = user.assigned_warehouses.all()
    if assigned.exists():
        return queryset.filter(warehouse__in=assigned)
    return queryset.none()


class InventoryCompatibilityView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        warehouse_id = request.query_params.get('warehouse')
        queryset = get_visible_stock_queryset(request.user)
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        
        data = []
        for stock in queryset:
            data.append({
                'id': stock.id,
                'product': stock.material.id,
                'product_name': stock.material.name,
                'quantity': stock.quantity,
                'warehouse': stock.warehouse.id,
                'batch_number': 'B-' + str(stock.id).zfill(3),
                'supplier': 'N/A',
                'created_at': stock.updated_at
            })
        return Response(data)

class ProductCompatibilityView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        type_filter = request.query_params.get('type') or request.query_params.get('category')
        warehouse_id = request.query_params.get('warehouse')
        queryset = Material.objects.all()
        if type_filter:
            queryset = queryset.filter(category=type_filter)
        visible_stock = get_visible_stock_queryset(request.user)
        if warehouse_id:
            visible_stock = visible_stock.filter(warehouse_id=warehouse_id)
        data = []
        for m in queryset:
            # Calculate total quantity across all warehouses
            total_qty = visible_stock.filter(material=m).aggregate(models.Sum('quantity'))['quantity__sum'] or 0
            data.append({
                'id': m.id,
                'name': m.name,
                'sku': m.sku or f'MAT-{m.id}',
                'type': m.get_category_display(),
                'category': m.category,
                'unit': m.unit,
                'price': float(m.price),
                'quantity': total_qty
            })
        return Response(data)

class DocumentCompatibilityView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = RawMaterialBatch.objects.all()
        data = []
        for b in queryset:
            data.append({
                'id': b.id,
                'number': b.invoice_number,
                'type': 'HISOB_FAKTURA_KIRIM',
                'date': b.date,
                'notes': f"Supplier: {b.supplier.name}",
                'responsiblePerson': b.responsible_user.full_name if b.responsible_user else 'Admin',
                'items': [
                    {'product': b.material.id, 'quantity': b.quantity_kg}
                ]
            })
        return Response(data)
    
    def post(self, request):
        # Support old kirim post
        data = request.data
        items = data.get('items', [])
        if not items:
            return Response({'error': 'No items'}, status=400)
        
        item = items[0]
        material_id = item.get('product')
        qty = item.get('quantity')
        
        from .models import Supplier, Material
        supplier_name = data.get('notes', '').replace('Supplier: ', '')
        supplier, _ = Supplier.objects.get_or_create(name=supplier_name or 'Unknown')
        material = Material.objects.get(id=material_id)
        
        batch = RawMaterialBatch.objects.create(
            supplier=supplier,
            material=material,
            quantity_kg=qty,
            invoice_number=data.get('number', 'AUTO'),
            batch_number=f"B-{timezone.now().strftime('%Y%m%d%H%M')}",
            responsible_user=request.user
        )
        return Response({'id': batch.id, 'status': 'created'})
