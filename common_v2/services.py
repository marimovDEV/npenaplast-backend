from .models import AuditLog

def log_action(user, action, module, description, object_id=None):
    """
    Utility to create an AuditLog entry.
    """
    return AuditLog.objects.create(
        user=user,
        action=action,
        module=module,
        description=description,
        object_id=str(object_id) if object_id else None
    )
