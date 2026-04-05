from django.db import transaction
from inventory.services import update_inventory
from .models import Transaction

def create_transaction(product, from_wh, to_wh, qty, trans_type, batch_number=None, batch=None, document=None, user=None, notes=''):
    """
    Creates a transaction record and updates the inventory atomically.
    Includes comprehensive audit trail (batch, document, user).
    """
    with transaction.atomic():
        if from_wh:
            # update_inventory will raise ValidationError if stock is insufficient
            update_inventory(product, from_wh, -qty, batch_number=batch_number)

        if to_wh:
            update_inventory(product, to_wh, qty, batch_number=batch_number)

        return Transaction.objects.create(
            product=product,
            from_warehouse=from_wh,
            to_warehouse=to_wh,
            quantity=qty,
            type=trans_type,
            batch_number=batch_number,
            batch=batch,
            document=document,
            user=user,
            notes=notes
        )
