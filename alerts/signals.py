"""
Alert triggers.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from warehouse_v2.models import Stock

@receiver(post_save, sender=Stock)
def check_low_stock_alert(sender, instance, **kwargs):
    """Xom ashyo kamayishi bo'yicha alert."""
    if instance.quantity <= 100:  # Threshold misol uchun 100 kg
        from .models import AlertRule, Alert
        
        rule = AlertRule.objects.filter(trigger_type='LOW_STOCK', is_active=True).first()
        if rule:
            # Check threshold if set
            if rule.threshold is not None and instance.quantity > rule.threshold:
                return
                
            # Create alert
            alert, created = Alert.objects.get_or_create(
                rule=rule,
                title=f"Xom ashyo kamaydi: {instance.material.name}",
                message=f"Sklad {instance.warehouse.name} da faqat {instance.quantity} kg {instance.material.name} qoldi.",
                severity='WARNING',
                is_resolved=False
            )
            
            if created:
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                from .serializers import AlertSerializer
                
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        'system_alerts',
                        {
                            'type': 'send_alert',
                            'alert': AlertSerializer(alert).data
                        }
                    )

@receiver(post_save, sender='production_v2.ProductionBatch')
def check_cost_anomaly_alert(sender, instance, **kwargs):
    """Tannarx oshib ketishi bo'yicha smart alert."""
    if instance.status != 'CLOSED':
        return
        
    from .models import SmartAnomalyRule, Alert
    from decimal import Decimal

    # Find the rule for production loss or expense spike
    rule = SmartAnomalyRule.objects.filter(anomaly_type='EXPENSE_SPIKE', is_active=True).first()
    if not rule:
        return

    # If unit_cost > threshold, trigger alert
    if instance.unit_cost > rule.normal_threshold:
        alert, created = Alert.objects.get_or_create(
            title=f"Tannarx Anomaliyasi: Batch {instance.batch_number}",
            message=f"Batch {instance.batch_number} uchun unit cost kutilganidan baland: {instance.unit_cost:,.2f} UZS. (Chegara: {rule.normal_threshold:,.2f})",
            severity='CRITICAL',
            is_resolved=False
        )
        
        if created:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            from .serializers import AlertSerializer
            
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    'system_alerts',
                    {
                        'type': 'send_alert',
                        'alert': AlertSerializer(alert).data
                    }
                )


@receiver(post_save, sender='sales_v2.Invoice')
def check_profitability_alert(sender, instance, **kwargs):
    """Sotuv foydashiligi tahlili (Phase 5)."""
    if instance.status != 'SHIPPED':
        return
        
    if instance.avg_margin_percent < 15:
        from .models import Alert
        severity = 'WARNING'
        label = 'PAST MARJA'
        
        if instance.avg_margin_percent < 0:
            severity = 'CRITICAL'
            label = 'ZARARGA SOTUV'
        elif instance.avg_margin_percent < 5:
            severity = 'CRITICAL'
            label = 'KRITIK MARJA'
            
        alert, created = Alert.objects.get_or_create(
            title=f"{label}: {instance.invoice_number}",
            message=f"Sotuv #{instance.invoice_number} uchun marja: {instance.avg_margin_percent:.1f}%. Foyda: {instance.total_profit:,.0f} UZS.",
            severity=severity,
            defaults={'is_resolved': False}
        )
        
        if created:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            from .serializers import AlertSerializer
            
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    'system_alerts',
                    {
                        'type': 'send_alert',
                        'alert': AlertSerializer(alert).data
                    }
                )
