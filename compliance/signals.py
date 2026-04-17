"""
Compliance validation signals to enforce business rules.
"""
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from warehouse_v2.models import Stock

@receiver(pre_save, sender=Stock)
def enforce_no_negative_stock(sender, instance, **kwargs):
    """Minus sklad taqiqlash qoidasi."""
    if instance.quantity < 0:
        from .models import ComplianceRule, ComplianceViolation
        
        # Check if rule exists and is active
        rule = ComplianceRule.objects.filter(rule_type='NEGATIVE_STOCK', is_active=True).first()
        if rule:
            # Log violation
            violation = ComplianceViolation.objects.create(
                rule=rule,
                description=f"Sklad {instance.warehouse.name} da minus balans kuzatildi: {instance.material.name} - {instance.quantity} kg",
                context_data={
                    'warehouse_id': instance.warehouse.id,
                    'material_id': instance.material.id,
                    'quantity': float(instance.quantity)
                }
            )
            
            # If severity is BLOCK, stop the operation
            if rule.severity == 'BLOCK':
                raise ValidationError(f"[COMPLIANCE] Minus sklad taqiqlangan! (Qoida buzilishi ID: {violation.id})")
