from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.http import FileResponse
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from datetime import timedelta
from warehouse_v2.models import RawMaterialBatch, Stock, Material
from production_v2.models import Zames, BlockProduction
from sales_v2.models import Invoice, SaleItem
from cnc_v2.models import WasteProcessing
from .models import ReportHistory
from .serializers import ReportHistorySerializer
from accounts.permissions import IsAdmin
from common_v2.mixins import NoDeleteMixin
from .services import generate_report_file


def _parse_start_date(raw_value, default_start):
    if not raw_value:
        return default_start
    if hasattr(raw_value, 'year'):
        return raw_value
    try:
        return timezone.datetime.fromisoformat(str(raw_value)).date()
    except ValueError:
        return default_start

class ReportHistoryViewSet(NoDeleteMixin, viewsets.ModelViewSet):
    queryset = ReportHistory.objects.all().order_by('-created_at')
    serializer_class = ReportHistorySerializer
    permission_classes = [IsAdmin]

    def perform_create(self, serializer):
        report = serializer.save(created_by=self.request.user, status='PENDING')
        generate_report_file(report)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        report = self.get_object()
        if not report.file_path:
            return Response({'error': 'Hisobot fayli topilmadi'}, status=404)
        filename = report.file_path.name.split('/')[-1]
        return FileResponse(report.file_path.open('rb'), as_attachment=True, filename=filename)

class GeneralAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        today = timezone.now().date()
        start_date = _parse_start_date(
            request.query_params.get('start_date'),
            today - timedelta(days=30),
        )
        valid_invoice_statuses = ['CONFIRMED', 'READY', 'SHIPPED', 'EN_ROUTE', 'DELIVERED', 'COMPLETED']
        
        # 1. KPIs
        total_sales = Invoice.objects.filter(
            date__date__gte=start_date,
            status__in=valid_invoice_statuses,
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        total_prod = BlockProduction.objects.filter(date__gte=start_date).aggregate(total=Sum('block_count'))['total'] or 0
        total_waste = WasteProcessing.objects.filter(date__date__gte=start_date).aggregate(total=Sum('waste_amount_kg'))['total'] or 0
        
        # stock_value = Sum(Stock.quantity * Material.price)
        stock_value = 0
        stocks = Stock.objects.all().select_related('material')
        for s in stocks:
            if s.material.price:
                stock_value += s.quantity * float(s.material.price)

        # 2. Charts (Daily Sales Trend)
        sales_trend = []
        for i in range(30, -1, -1):
            day = today - timedelta(days=i)
            day_sales = Invoice.objects.filter(
                date__date=day,
                status__in=valid_invoice_statuses,
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            if day_sales > 0 or i < 7: # Keep at least last 7 days
                sales_trend.append({
                    'date': day.strftime('%d.%m'),
                    'value': float(day_sales)
                })

        return Response({
            'kpis': {
                'total_sales': float(total_sales),
                'total_production': int(total_prod),
                'total_waste_kg': float(total_waste),
                'waste_per_block_kg': round((total_waste / total_prod), 4) if total_prod > 0 else 0,
                'stock_value': float(stock_value)
            },
            'charts': {
                'sales_trend': sales_trend,
                'waste_distribution': [
                    {'name': 'CNC', 'value': 65},
                    {'name': 'Ishlab chiqarish', 'value': 25},
                    {'name': 'Pardozlash', 'value': 10},
                ]
            }
        })

class RawMaterialReportView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        report = RawMaterialBatch.objects.values('supplier__name', 'supplier_name').annotate(
            total_kg=Sum('quantity_kg'),
            batch_count=Count('id')
        )
        return Response([
            {
                'supplier': row['supplier__name'] or row['supplier_name'] or 'Noma\'lum',
                'total_kg': row['total_kg'],
                'batch_count': row['batch_count'],
            }
            for row in report
        ])

class ProductionEfficiencyView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        report = Zames.objects.all().aggregate(
            total_input=Sum('input_weight'),
            total_output=Sum('output_weight'),
            total_dried=Sum('dried_weight'),
        )
        total_input = report['total_input'] or 0
        total_output = report['total_output'] or 0
        report['efficiency_percent'] = round((total_output / total_input) * 100, 2) if total_input else 0
        return Response(report)

class WarehouseBalanceView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        balances = Stock.objects.values('warehouse__name', 'material__name').annotate(
            total_quantity=F('quantity')
        )
        return Response([
            {
                'warehouse': row['warehouse__name'],
                'material': row['material__name'],
                'total_quantity': row['total_quantity'],
            }
            for row in balances
        ])

class SalesReportView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        report = Invoice.objects.exclude(status='CANCELLED').aggregate(
            total_revenue=Sum('total_amount'),
            invoice_count=Count('id')
        )
        return Response(report)
