from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from sales_v2.models import Invoice, Customer
from alerts.models import Alert

def detect_overdue_debts():
    """
    Identifies debts older than 30 days and updates ClientBalance and Customer health.
    (Enterprise Phase 6)
    """
    from .models import ClientBalance
    
    # Standard overdue period: 30 days
    overdue_threshold = timezone.now() - timedelta(days=30)
    
    with transaction.atomic():
        balances = ClientBalance.objects.select_for_update().filter(total_debt__gt=0)
        
        for cb in balances:
            # Find all unpaid/partially paid invoices that are DEBT and > 30 days old
            # Note: For now we assume if status is not COMPLETED/CANCELLED and payment is DEBT, it's a pending debt.
            overdue_invoices = Invoice.objects.filter(
                customer=cb.customer,
                payment_method='DEBT',
                date__lte=overdue_threshold,
                status__in=['SHIPPED', 'EN_ROUTE', 'DELIVERED'] # Items already received but not "COMPLETED" (paid)
            )
            
            overdue_sum = overdue_invoices.aggregate(s=Sum('total_amount'))['s'] or Decimal('0')
            cb.overdue_debt = overdue_sum
            cb.save()
            
            # Update Customer Status if overdue debt exists
            if overdue_sum > 0:
                customer = cb.customer
                customer.debt_status = 'OVERDUE'
                customer.segment = 'RISK' # Escalation to RISK segment
                customer.save()
                
                # Create Alert for manager
                Alert.objects.get_or_create(
                    title=f"MUDDATI O'TGAN QARZ: {customer.name}",
                    message=f"Mijoz {customer.name} ning {overdue_sum:,.0f} UZS qarzi 30 kundan oshdi.",
                    severity='CRITICAL',
                    defaults={'is_resolved': False}
                )

    return True
