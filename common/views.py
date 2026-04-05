from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from products.models import Product, ProductionTask
from warehouse.models import Warehouse
from inventory.models import InventoryBatch
from documents.models import Document, DocumentItem
from sales.models import SalesOrder, Client
from .models import AuditLog
from .serializers import AuditLogSerializer

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    filterset_fields = ('module', 'action', 'user')

class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. Total Materials (Granula) from Sklad 1
        mat_qty = InventoryBatch.objects.filter(location__name__icontains='Sklad 1').aggregate(total=Sum('current_weight'))['total'] or 0
        
        # 2. Finished Blocks from Sklad 2
        block_qty = InventoryBatch.objects.filter(location__name__icontains='Sklad 2').aggregate(total=Sum('current_weight'))['total'] or 0
        
        # 3. Finished Products from Sklad 4
        product_qty = InventoryBatch.objects.filter(location__name__icontains='Sklad 4').aggregate(total=Sum('current_weight'))['total'] or 0
        
        # 4. Waste
        waste_qty = InventoryBatch.objects.filter(location__type='Waste').aggregate(total=Sum('current_weight'))['total'] or 0

        # 6. Bunkers Status
        bunkers = Warehouse.objects.filter(type='Bunker').order_by('name')
        bunker_data = []
        for b in bunkers:
             # Basic logic: if has inventory > 0, it's not empty
             inv = InventoryBatch.objects.filter(location=b).aggregate(total=Sum('current_weight'))['total'] or 0
             status = 'Empty' if inv == 0 else 'In Use' # Simplified
             bunker_data.append({'id': b.id, 'name': b.name, 'status': status})

        # 7. Production stage counts
        cnc_count = ProductionTask.objects.filter(stage='CNC', is_completed=False).count()
        fin_count = ProductionTask.objects.filter(stage__in=['FINISHING', 'DRYING'], is_completed=False).count()

        # 8. Recent Sales
        recent_sales = Document.objects.filter(type='HISOB_FAKTURA_CHIQIM').order_by('-created_at')[:5]
        sales_data = []
        for s in recent_sales:
            sales_data.append({
                'id': s.id, 
                'clientName': s.client.name if s.client else 'Noma\'lum',
                'itemName': s.items.first().product.name if s.items.exists() else 'Mahsulot',
                'date': s.created_at,
                'status': 'Tayyor'
            })

        # 8. Monthly Stats (Last 30 days)
        last_month = timezone.now() - timedelta(days=30)
        
        # Monthly Production (sum of quantities from production tasks completed in last 30 days)
        monthly_prod = ProductionTask.objects.filter(is_completed=True, updated_at__gte=last_month).aggregate(total=Sum('quantity'))['total'] or 0
        
        # Monthly Sales Revenue
        monthly_sales_docs = Document.objects.filter(type='HISOB_FAKTURA_CHIQIM', created_at__gte=last_month)
        monthly_revenue = 0
        for doc in monthly_sales_docs:
            for item in doc.items.all():
                monthly_revenue += item.quantity * (item.product.price or 0)

        # Waste Rate
        total_produced = ProductionTask.objects.filter(is_completed=True).aggregate(total=Sum('quantity'))['total'] or 1
        total_waste = InventoryBatch.objects.filter(location__type='Waste').aggregate(total=Sum('current_weight'))['total'] or 0
        waste_rate = (total_waste / (total_produced + total_waste)) * 100

        # 8. Salesperson specific metrics
        today = Document.objects.filter(type='HISOB_FAKTURA_CHIQIM', created_at__date=timezone.now().date()).count() 
        active_orders = SalesOrder.objects.exclude(status__in=['SHIPPED', 'CANCELLED']).count()
        client_count = Client.objects.count()
        total_debt = Client.objects.aggregate(total=Sum('balance'))['total'] or 0

        # 9. Recent Kirim
        recent_kirims = Document.objects.filter(type='HISOB_FAKTURA_KIRIM').order_by('-created_at')[:5]
        kirim_data = []
        for k in recent_kirims:
            kirim_data.append({
                'id': k.id,
                'supplier': k.number or "Yetkazib beruvchi",
                'batchNumber': k.number or f"B-{k.id}",
                'quantity': sum(i.quantity for i in k.items.all()),
                'date': k.created_at.strftime('%d.%m.%Y')
            })

        # 10. Chart Data (Last 7 Days)
        chart_data = []
        for i in range(6, -1, -1):
            day = timezone.now().date() - timedelta(days=i)
            day_name = ['Yak', 'Dush', 'Sesh', 'Chor', 'Pay', 'Jum', 'Shan'][day.weekday()]
            
            p_qty = ProductionTask.objects.filter(is_completed=True, updated_at__date=day).aggregate(total=Sum('quantity'))['total'] or 0
            s_qty = DocumentItem.objects.filter(document__type='HISOB_FAKTURA_CHIQIM', document__created_at__date=day).aggregate(total=Sum('quantity'))['total'] or 0
            d_qty = ProductionTask.objects.filter(stage='CNC', created_at__date=day).aggregate(total=Sum('quantity'))['total'] or 0
            
            chart_data.append({
                'name': day_name,
                'prod': p_qty,
                'sales': s_qty,
                'dekor': d_qty
            })

        return Response({
            'stats': [
                {'name': 'Xom Ashyo (Granula)', 'value': f"{int(mat_qty):,} kg", 'icon': 'Database', 'color': 'bg-blue-600'},
                {'name': 'Tayyor Bloklar', 'value': f"{int(block_qty):,} dona", 'icon': 'Layers', 'color': 'bg-emerald-600'},
                {'name': 'Pardozlangan', 'value': f"{int(product_qty):,} dona", 'icon': 'Box', 'color': 'bg-indigo-600'},
                {'name': 'Brak/Chiqindi', 'value': f"{int(waste_qty):,} kg", 'icon': 'Trash2', 'color': 'bg-rose-500'},
            ],
            'salesStats': [
                {'name': "Bugungi Sotuv", 'value': str(today), 'icon': 'ShoppingCart', 'color': 'bg-blue-600'},
                {'name': "Aktiv Buyurtmalar", 'value': str(active_orders), 'icon': 'Package', 'color': 'bg-emerald-600'},
                {'name': "Mijozlar Soni", 'value': str(client_count), 'icon': 'UserIcon', 'color': 'bg-indigo-600'},
                {'name': "Umumiy Qarzdorlik", 'value': f"{float(total_debt)/1e6:.1f} mln", 'icon': 'DollarSign', 'color': 'bg-rose-500'},
            ],
            'adminStats': [
                {'name': "Oylik Ishlab Chiqarish", 'value': f"{int(monthly_prod):,} m3", 'growth': '+12.5%', 'trend': 'up'},
                {'name': "Oylik Sotuv", 'value': f"{monthly_revenue/1e6:.1f} mln UzS", 'growth': '+8.2%', 'trend': 'up'},
                {'name': "Chiqindi Ulushi", 'value': f"{waste_rate:.1f}%", 'growth': '-1.2%', 'trend': 'down'},
            ],
            'chartData': chart_data,
            'bunkers': bunker_data,
            'counts': {
                'cnc': cnc_count,
                'finishing': fin_count
            },
            'overdueCount': SalesOrder.objects.filter(deadline__lt=timezone.now()).exclude(status__in=['SHIPPED', 'CANCELLED']).count(), 
            'recentSales': sales_data,
            'recentKirim': kirim_data,
        })
