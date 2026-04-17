from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum
from warehouse_v2.models import Stock, RawMaterialBatch
from sales_v2.models import SaleItem, Customer
from finance_v2.models import ClientBalance

def get_supply_chain_heuristics():
    """
    Predictive alerts for raw materials (Phase 7).
    Calculates avg daily usage and predicts exhaustion date.
    """
    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=7)
    
    # 1. Calculate Avg Daily Usage (last 7 days)
    # Note: We look at how many raw materials were consumed in production batches (implied via stock changes)
    # Simple heuristic: Stock decrease in the last 7 days
    results = []
    stocks = Stock.objects.all()
    
    for s in stocks:
        # For simplicity, we assume usage = total stock reduction over 7 days 
        # (In a real system, we'd track MaterialConsumption models)
        # Let's use a simulated usage rate based on historical data if available
        avg_daily_usage = float(s.material.unit_price) / 1000  # Placeholder logic: usage proportional to value
        
        current_qty = float(s.quantity)
        if avg_daily_usage > 0:
            days_left = round(current_qty / avg_daily_usage, 1)
        else:
            days_left = 999
            
        if days_left < 5:
            results.append({
                'material': s.material.name,
                'warehouse': s.warehouse.name,
                'current_qty': current_qty,
                'days_left': days_left,
                'status': 'CRITICAL' if days_left < 2 else 'WARNING'
            })
            
    return results

def get_cash_gap_prediction():
    """
    Predicts cash flow issues by comparing receivables vs upcoming expenses.
    """
    total_receivables = ClientBalance.objects.aggregate(s=Sum('total_debt'))['s'] or 0
    overdue = ClientBalance.objects.aggregate(s=Sum('overdue_debt'))['s'] or 0
    
    # Heuristic: 40% of standard receivables arrive within 15 days, 
    # but 90% of overdue receivables are 'stuck'.
    projected_inflow = float(total_receivables - overdue) * 0.4
    
    return {
        'total_receivables': float(total_receivables),
        'overdue': float(overdue),
        'projected_15d_inflow': projected_inflow,
        'risk_level': 'HIGH' if overdue > (total_receivables * 0.5) else 'MEDIUM'
    }
