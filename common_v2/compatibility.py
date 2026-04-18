from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from datetime import timedelta

from accounts.permissions import get_user_role_name

from warehouse_v2.models import Stock, RawMaterialBatch, Warehouse
from production_v2.models import Zames, Bunker, BlockProduction, BunkerLoad
from sales_v2.models import Invoice, SaleItem
from cnc_v2.models import CNCJob, WasteProcessing

class DashboardCompatibilityView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _can_view_all_warehouses(self, user, role_name):
        return user.is_superuser or role_name in [
            'Bosh Admin', 'Admin', 'SUPERADMIN', 'ADMIN', 'Sotuv menejeri', 'SALES_MANAGER', 'Kuryer', 'COURIER'
        ]

    def _get_visible_stocks(self, user, role_name):
        queryset = Stock.objects.all()
        if self._can_view_all_warehouses(user, role_name):
            return queryset

        assigned_warehouses = user.assigned_warehouses.all()
        if assigned_warehouses.exists():
            return queryset.filter(warehouse__in=assigned_warehouses)
        return queryset.none()

    def _get_visible_invoices(self, user, role_name, valid_statuses):
        queryset = Invoice.objects.filter(status__in=valid_statuses)
        if user.is_superuser or role_name in ['Bosh Admin', 'Admin', 'SUPERADMIN', 'ADMIN']:
            return queryset
        if role_name in ['Sotuv menejeri', 'SALES_MANAGER']:
            return queryset.filter(
                Q(created_by=user) | Q(customer__assigned_manager=user)
            ).distinct()
        if role_name in ['Kuryer', 'COURIER']:
            return queryset.filter(delivery__courier=user)
        return queryset.none()

    def _get_visible_raw_batches(self, user, role_name):
        queryset = RawMaterialBatch.objects.all()
        if user.is_superuser or role_name in ['Bosh Admin', 'Admin', 'SUPERADMIN', 'ADMIN']:
            return queryset
        if role_name not in ['Omborchi', 'WAREHOUSE_OPERATOR']:
            return queryset.none()

        assigned_warehouses = user.assigned_warehouses.all()
        if assigned_warehouses.filter(name__icontains='Sklad №1').exists():
            return queryset
        return queryset.none()

    def get(self, request):
        user = request.user
        role_name = get_user_role_name(user)
        period = request.query_params.get('period', 'week')
        today = timezone.now().date()
        valid_invoice_statuses = ['NEW', 'CONFIRMED', 'IN_PRODUCTION', 'READY', 'SHIPPED', 'EN_ROUTE', 'DELIVERED', 'COMPLETED']
        
        if period == 'day':
            start_date = today
        elif period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        else:
            start_date = today - timedelta(days=7)

        visible_stocks = self._get_visible_stocks(user, role_name)
        visible_invoices = self._get_visible_invoices(user, role_name, valid_invoice_statuses)
        visible_raw_batches = self._get_visible_raw_batches(user, role_name)

        # 1. Real-time Warehouse Stats (KPI Cards)
        mat_qty = visible_stocks.filter(warehouse__name__icontains='Sklad №1').aggregate(total=Sum('quantity'))['total'] or 0
        block_qty = visible_stocks.filter(warehouse__name__icontains='Sklad №2').aggregate(total=Sum('quantity'))['total'] or 0
        product_qty = visible_stocks.filter(warehouse__name__icontains='Sklad №4').aggregate(total=Sum('quantity'))['total'] or 0
        semi_qty = visible_stocks.filter(warehouse__name__icontains='Sklad №3').aggregate(total=Sum('quantity'))['total'] or 0
        
        # 2. Period Statistics (KPIs below)
        today_intake = visible_raw_batches.filter(date__gte=start_date).aggregate(total=Sum('quantity_kg'))['total'] or 0
        today_prod_blocks = BlockProduction.objects.filter(date__gte=start_date).aggregate(total=Sum('block_count'))['total'] or 0
        today_sales_count = visible_invoices.filter(date__date__gte=start_date).count()
        today_waste = WasteProcessing.objects.filter(date__date__gte=start_date).aggregate(total=Sum('waste_amount_kg'))['total'] or 0
        
        # 3. Production Pipeline Stage Counts (These are "current active" status)
        active_zames = Zames.objects.filter(status='IN_PROGRESS').count()
        
        # Bunkers status
        bunkers_data = []
        for b in Bunker.objects.all():
            last_load = BunkerLoad.objects.filter(bunker=b).order_by('-load_time').first()
            status = 'Empty'
            if last_load:
                is_used = BlockProduction.objects.filter(zames=last_load.zames).exists()
                if not is_used:
                    status = 'Ready' if (timezone.now() - last_load.load_time).total_seconds() / 60 > last_load.required_time else 'Drying'
            bunkers_data.append({
                'id': b.id,
                'name': b.name,
                'status': status
            })
            
        active_cnc = CNCJob.objects.filter(created_at__date=today).count()
        from finishing_v2.models import FinishingJob
        active_finishing = FinishingJob.objects.filter(status__in=['PENDING', 'RUNNING']).count()
        
        # 4. Chart Data (Based on period)
        chart_limit = 7 if period == 'week' else (30 if period == 'month' else 1)
        chart_data = []
        for i in range(chart_limit - 1, -1, -1):
            day = today - timedelta(days=i)
            day_name = day.strftime('%d.%m') if period == 'month' else ['Dush', 'Sesh', 'Chor', 'Pay', 'Jum', 'Shan', 'Yak'][day.weekday()]
            
            p_qty = BlockProduction.objects.filter(date=day).aggregate(total=Sum('block_count'))['total'] or 0
            day_invoice_ids = visible_invoices.filter(date__date=day).values('id')
            s_qty = SaleItem.objects.filter(invoice_id__in=day_invoice_ids).aggregate(total=Sum('quantity'))['total'] or 0
            
            chart_data.append({
                'name': day_name,
                'prod': p_qty,
                'sales': s_qty,
                'dekor': 0
            })

        # 5. Strategic Data for Decision Engine (Phase 10)
        from reports_v2.services import get_profitability_summary, get_inventory_valuation
        from reports_v2.heuristics import get_supply_chain_heuristics, get_cash_gap_prediction, get_top_business_metrics
        
        prof_summary = get_profitability_summary('This Month')
        inventory_valuation = get_inventory_valuation()
        
        # Calculate Strategic KPIs
        total_revenue = Invoice.objects.filter(
            date__date__gte=start_date,
            status__in=['CONFIRMED', 'READY', 'SHIPPED', 'EN_ROUTE', 'DELIVERED', 'COMPLETED']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        net_profit = prof_summary['total_profit']
        
        heuristics = {
            'supply_alerts': get_supply_chain_heuristics(),
            'cash_prediction': get_cash_gap_prediction(),
            'strategic_metrics': get_top_business_metrics()
        }

        # 6. Document Stats
        doc_stats = [
            {'name': "Hisob-faktura", 'value': str(visible_invoices.filter(date__date__gte=start_date).count())},
            {'name': "Nakladnoy", 'value': str(visible_raw_batches.filter(date__gte=start_date).count())},
            {'name': "Buyurtma-naryad", 'value': str(CNCJob.objects.filter(created_at__date__gte=start_date).count())},
        ]

        overdue_count = visible_invoices.filter(
            status__in=['NEW', 'CONFIRMED', 'IN_PRODUCTION', 'READY'],
            date__date__lt=today - timedelta(days=3)
        ).count()

        return Response({
            'strategicKpis': [
                {'name': 'Sof Foyda', 'value': f"{int(net_profit):,} UZS", 'trend': '+8.4%', 'color': 'emerald'},
                {'name': 'Tushum', 'value': f"{int(total_revenue):,} UZS", 'trend': '+12.1%', 'color': 'blue'},
                {'name': 'Xarajatlar', 'value': f"{int(total_revenue - net_profit):,} UZS", 'trend': '-2.3%', 'color': 'rose'},
                {'name': 'Ombor Qiymati', 'value': f"{int(inventory_valuation):,} UZS", 'trend': '+3.5%', 'color': 'amber'},
            ],
            'stats': [
                {'name': 'Xom Ashyo (Sklad 1)', 'value': f"{int(mat_qty):,} kg", 'icon': 'Database', 'color': 'bg-blue-600'},
                {'name': 'Bloklar (Sklad 2)', 'value': f"{int(block_qty):,} dona", 'icon': 'Layers', 'color': 'bg-emerald-600'},
                {'name': 'Yarim Tayyor (Sklad 3)', 'value': f"{int(semi_qty):,} dona", 'icon': 'Package', 'color': 'bg-amber-600'},
                {'name': 'Tayyor Mahsulot (Sklad 4)', 'value': f"{int(product_qty):,} dona", 'icon': 'Box', 'color': 'bg-indigo-600'},
            ],
            'todayStats': {
                'intake': f"{int(today_intake):,} kg",
                'production': f"{int(today_prod_blocks):,} dona",
                'waste': f"{int(today_waste):,} kg",
                'sales_count': today_sales_count
            },
            'pipeline': {
                'zames': active_zames,
                'bunkers': bunkers_data,
                'cnc': active_cnc,
                'finishing': active_finishing
            },
            'docStats': doc_stats,
            'chartData': chart_data,
            'heuristics': heuristics,
            'recentSales': list(visible_invoices.order_by('-date')[:5].values(
                'id', 'invoice_number', 'customer__name', 'total_amount', 'status', 'date'
            )),
            'overdueCount': overdue_count
        })
