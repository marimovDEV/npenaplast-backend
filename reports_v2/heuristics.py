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
        current_qty = float(s.quantity)
        min_qty = float(s.min_level)
        
        if min_qty > 0 and current_qty <= min_qty:
            days_left = 1 if current_qty == 0 else round(current_qty / min_qty * 3, 1) # simple estimation
            priority = 'CRITICAL' if current_qty <= (min_qty * 0.5) else 'WARNING'
            results.append({
                'id': f"supply_{s.id}",
                'material': s.material.name,
                'warehouse': s.warehouse.name,
                'days_left': days_left,
                'status': priority,
                'priority': 0 if priority == 'CRITICAL' else 1,
                'action_type': 'ORDER',
                'action_label': 'Zakaz berish',
                'message': f"{s.material.name} zaxirasi minimal darajaga yetdi ({current_qty} qoldi)."
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
    Strategic insights for the Decision Engine.
    Identifies the single biggest Risk and Opportunity dynamically.
    """
    # 1. RISK: Overdue debts
    overdue_debt = ClientBalance.objects.aggregate(s=Sum('overdue_debt'))['s'] or 0
    risk = {
        'title': 'Eng katta xavf',
        'type': 'RISK',
        'content': 'Qarzdorlik oshmoqda',
        'value': f"{int(overdue_debt):,} UZS",
        'description': 'Debitorlik qarzining muddati o\'tgan qismi oshib bormoqda. Tezroq undirish zarur.',
        'action_label': 'Tahlil qilish',
        'tab_id': 'debtors'
    }

    # 2. OPPORTUNITY: High margin/selling products
    thirty_days_ago = timezone.now() - timedelta(days=30)
    top_sale = SaleItem.objects.filter(invoice__date__gte=thirty_days_ago).values('product__name').annotate(
        total_profit=Sum('profit')
    ).order_by('-total_profit').first()

    if top_sale and top_sale['total_profit'] > 0:
        opp_name = top_sale['product__name']
        opp_val = top_sale['total_profit']
        content = f"{opp_name}"
        value = f"{int(opp_val):,} UZS foyda"
        desc = "Ushbu mahsulot oxirgi 30 kunda eng ko'p foyda keltirgan. Zaxirasini yetarli saqlash tavsiya qilinadi."
    else:
        content = "Sotuv ma'lumotlari kam"
        value = "Tahlil qilinmoqda"
        desc = "Kutib turing. Yetarli ma'lumot yig'ilmagan."

    opportunity = {
        'title': 'Eng katta imkoniyat',
        'type': 'OPPORTUNITY',
        'content': content,
        'value': value,
        'description': desc,
        'action_label': 'Rejalashtirish',
        'tab_id': 'production'
    }

    return [risk, opportunity]
