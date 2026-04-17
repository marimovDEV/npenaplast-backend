"""
Advanced Field-Level Permissions and Strict Workflows
"""
from rest_framework import permissions

class FieldLevelPermissionMixin:
    """
    Serializer mixin to dynamically remove fields based on the user's role.
    Example usage in a Serializer:
        restricted_fields = {
            'Buxgalter': [], # sees all
            'Operator': ['price', 'total_amount'] # cannot see pricing
        }
    """
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        
        if request and request.user.is_authenticated:
            # Check user role and filter fields
            role = request.user.role.name if request.user.role else None
            if hasattr(self.Meta, 'restricted_fields') and role in self.Meta.restricted_fields:
                fields_to_hide = self.Meta.restricted_fields[role]
                for field in fields_to_hide:
                    data.pop(field, None)
        return data

def enforce_strict_workflow(instance, allowed_transitions):
    """
    Helper function to check if a status transition is allowed.
    allowed_transitions = {
        'DRAFT': ['PENDING', 'CANCELLED'],
        'PENDING': ['APPROVED', 'REJECTED'],
        'APPROVED': ['EXECUTED'],
        'EXECUTED': ['CLOSED']
    }
    """
    from django.core.exceptions import ValidationError
    
    # Must tracking old vs new status via audit log logic or model __init__ state
    # This acts as a centralized checker.
    if hasattr(instance, '_original_status'):
        current_status = instance._original_status
        new_status = instance.status
        
        if current_status != new_status:
            valid_next = allowed_transitions.get(current_status, [])
            if new_status not in valid_next:
                raise ValidationError(f"FINAL ENTERPRISE: Ruxsat etilmagan status o'zgarishi: {current_status} -> {new_status}. Faqat {valid_next} ga ruxsat berilgan.")
