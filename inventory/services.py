from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import InventoryBatch, InventoryMovement, ProductSource

def update_inventory(product, warehouse, qty, batch_number=None, source=ProductSource.EXTERNAL, user=None, reference="", notes=""):
    """
    Updates or creates an inventory batch and records a movement.
    qty can be positive (kirim) or negative (chiqim).
    """
    with transaction.atomic():
        # 1. Handle Batch
        batch, created = InventoryBatch.objects.select_for_update().get_or_create(
            product=product,
            batch_number=batch_number,
            defaults={
                'initial_weight': qty if qty > 0 else 0,
                'current_weight': 0,
                'location': warehouse,
                'source': source
            }
        )
        
        from decimal import Decimal
        qty_dec = Decimal(str(qty))
        
        if batch.current_weight + qty_dec < 0:
            raise ValidationError(f"Yetersiz qoldiq: {product.name} (Partiya: {batch_number}). Mavjud: {batch.current_weight}, Talab: {abs(qty)}")
        
        batch.current_weight += qty_dec
        if batch.current_weight == 0:
            batch.status = 'DEPLETED'
        else:
            batch.status = 'IN_STOCK'
        
        batch.location = warehouse
        batch.save()

        # 2. Record Movement
        movement_type = 'IN' if qty > 0 else 'OUT'
        InventoryMovement.objects.create(
            batch=batch,
            from_location=warehouse if qty < 0 else None,
            to_location=warehouse if qty > 0 else None,
            quantity=abs(qty),
            type=movement_type,
            reference=reference,
            performed_by=user,
            notes=notes
        )

        # 3. Update V2 Stock (Aggregate)
        from warehouse_v2.models import Stock
        stock_obj, _ = Stock.objects.get_or_create(
            warehouse_id=warehouse.id,
            material_id=product.id,
            defaults={'quantity': 0}
        )
        stock_obj.quantity += float(qty)
        stock_obj.save()

        return batch

def check_stock(product, warehouse, qty, batch_number=None):
    """
    Checks if enough stock exists in a specific batch.
    """
    try:
        batch = InventoryBatch.objects.get(product=product, batch_number=batch_number)
        return batch.current_weight >= qty
    except InventoryBatch.DoesNotExist:
        return False

def get_stock_balance(product, warehouse, batch_number=None):
    """
    Returns current stock balance for a batch.
    """
    try:
        batch = InventoryBatch.objects.get(product=product, batch_number=batch_number)
        return batch.current_weight
    except InventoryBatch.DoesNotExist:
        return 0
