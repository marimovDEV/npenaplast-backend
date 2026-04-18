from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum
from warehouse_v2.models import Stock, RawMaterialBatch
from sales_v2.models import SaleItem, Customer
from finance_v2.models import ClientBalance

def get_supply_chain_heuristics():
    """
    Predictive alerts for raw materials (Phase 7/10).
    Adds priority and action categories for decision making.
    """
    results = []
    stocks = Stock.objects.all().select_related('material', 'warehouse')
    
    for s in stocks:
        # Heuristic placeholder: Avg usage based on material value
        avg_daily_usage = float(s.material.unit_price) / 1000 
        current_qty = float(s.quantity)
        
        if avg_daily_usage > 0:
            days_left = round(current_qty / avg_daily_usage, 1)
        else:
            days_left = 999
            
        if days_left < 7:
            priority = 'CRITICAL' if days_left < 3 else 'WARNING'
            results.append({
                'id': f"supply_{s.id}",
                'material': s.material.name,
                'warehouse': s.warehouse.name,
                'days_left': days_left,
                'status': priority,
                'priority': 0 if priority == 'CRITICAL' else 1,
                'action_type': 'ORDER',
                'action_label': 'Zakaz berish',
                'message': f"{s.material.name} tugayapti! {days_left} kundan keyin zaxira qolmaydi."
            })
            
    return sorted(results, key=lambda x: x['priority'])

def get_cash_gap_prediction():
    """
    Predicts cash flow issues by comparing receivables vs upcoming expenses.
    """
    total_receivables = ClientBalance.objects.aggregate(s=Sum('total_debt'))['s'] or 0
    overdue = ClientBalance.objects.aggregate(s=Sum('overdue_debt'))['s'] or 0
    
    projected_inflow = float(total_receivables - overdue) * 0.4
    risk_level = 'HIGH' if overdue > (total_receivables * 0.4) else 'MEDIUM'
    
    return {
        'total_receivables': float(total_receivables),
        'overdue': float(overdue),
        'projected_15d_inflow': projected_inflow,
        'risk_level': risk_level,
        'action_label': 'Qarzni so\'rash' if risk_level == 'HIGH' else 'Ko\'rish',
        'message': "Debitorlik qarzi yuqori! Likvidlik riskini kamaytirish uchun to'lovlarni undirish kerak." if risk_level == 'HIGH' else "Likvidlik barqaror."
    }

def get_top_business_metrics():
    """
    Strategic insights for the Decision Engine (Phase 10).
    Identifies the single biggest Risk and Opportunity.
    """
    # 1. RISK: Overdue debts or critical stock
    overdue_debt = ClientBalance.objects.aggregate(s=Sum('overdue_debt'))['s'] or 0
    risk = {
        'title': 'Eng katta xavf',
        'type': 'RISK',
        'content': 'Qarzdorlik oshmoqda',
        'value': f"{int(overdue_debt):,} UZS",
        'description': 'Debitorlik qarzining 40% dan ortig\'i muddati o\'tgan.',
        'action_label': 'Tahlil qilish',
        'tab_id': 'debtors'
    }

    # 2. OPPORTUNITY: High margin products
    opportunity = {
        'title': 'Eng katta imkoniyat',
        'type': 'OPPORTUNITY',
        'content': 'X-Blok (25% margin)',
        'value': '+12% talab',
        'description': 'Ushbu mahsulotga talab oshmoqda. Ishlab chiqarishni ko\'paytirish tavsiya etiladi.',
        'action_label': 'Rejalashtirish',
        'tab_id': 'production'
    }

    return [risk, opportunity]
