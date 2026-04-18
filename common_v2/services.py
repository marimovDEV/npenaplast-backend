from .models import AuditLog

def log_action(user, action, module, description, object_id=None, old_value=None, new_value=None, model_name=None):
    """
    Utility to create an AuditLog entry with change tracking.
    """
    return AuditLog.objects.create(
        user=user,
        action=action,
        module=module,
        description=description,
        object_id=str(object_id) if object_id else None,
        old_value=old_value,
        new_value=new_value,
        model_name=model_name
    )
