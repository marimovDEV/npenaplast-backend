from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from common_v2.services import log_action
from .models import InventoryBatch, InventoryMovement, ProductSource

def update_inventory(product, warehouse, qty, batch_number=None, source=ProductSource.EXTERNAL, user=None, reference="", notes=""):
    """
    Centralized Inventory Service Layer.
    Updates or creates an inventory batch and records an aggregate stock movement.
    qty can be positive (kirim) or negative (chiqim).
    
    Enforces Atomicity, Concurrency Protection (Locking), and Decimal Precision.
    """
    if not warehouse:
        raise ValidationError("Ombor ko'rsatilmadi.")
    if not product:
        raise ValidationError("Mahsulot ko'rsatilmadi.")
        
    qty_dec = Decimal(str(qty))
    
    with transaction.atomic():
        # 1. Lock and Update/Create the individual Batch
        batch, created = InventoryBatch.objects.select_for_update().get_or_create(
            product=product,
            batch_number=batch_number,
            defaults={
                'initial_weight': qty_dec if qty_dec > 0 else Decimal('0'),
                'current_weight': Decimal('0'),
                'location': warehouse,
                'source': source,
                'status': 'IN_STOCK'
            }
        )
        
        if batch.current_weight + qty_dec < 0:
            raise ValidationError({
                "inventory": f"Yetersiz qoldiq: {product.name} (Partiya: {batch_number}). " \
                             f"Omborda: {batch.current_weight} {product.unit}, So'ralgan: {abs(qty_dec)} {product.unit}"
            })
        
        old_batch_weight = batch.current_weight
        batch.current_weight += qty_dec
        batch.status = 'DEPLETED' if batch.current_weight <= 0 else 'IN_STOCK'
        batch.location = warehouse # Ensure location is updated if batch moved
        batch.save()
        
        # 2. Record Detailed Movement Log
        movement_type = 'IN' if qty_dec > 0 else 'OUT'
        movement = InventoryMovement.objects.create(
            batch=batch,
            from_location=warehouse if qty_dec < 0 else None,
            to_location=warehouse if qty_dec > 0 else None,
            quantity=abs(qty_dec),
            type=movement_type,
            reference=reference,
            performed_by=user,
            notes=notes
        )
        
        # 3. Lock and Update the Aggregate Stock (warehouse_v2.Stock)
        from warehouse_v2.models import Stock
        stock_obj, _ = Stock.objects.select_for_update().get_or_create(
            warehouse=warehouse,
            material=product,
            defaults={'quantity': Decimal('0')}
        )
        
        old_stock_qty = stock_obj.quantity
        stock_obj.quantity += qty_dec
        stock_obj.save()
        
        # 4. Enterprise Audit Logging
        log_action(
            user=user,
            action='TRANSFER' if reference else ('CREATE' if qty_dec > 0 else 'UPDATE'),
            module='Inventory',
            description=f"Invertar yangilandi: {product.name} ({qty_dec} {product.unit})",
            object_id=batch.id,
            old_value={'batch_weight': float(old_batch_weight), 'total_stock': float(old_stock_qty)},
            new_value={'batch_weight': float(batch.current_weight), 'total_stock': float(stock_obj.quantity)}
        )
        
        return batch

def check_stock(product, warehouse, qty, batch_number=None):
    """
    High-performance stock check (no locking).
    """
    try:
        qty_dec = Decimal(str(qty))
    except (TypeError, ValueError):
        return False
        
    try:
        if batch_number:
            batch = InventoryBatch.objects.get(product=product, batch_number=batch_number, location=warehouse)
            return batch.current_weight >= qty_dec
        else:
            from warehouse_v2.models import Stock
            stock = Stock.objects.get(warehouse=warehouse, material=product)
            return stock.quantity >= qty_dec
    except (InventoryBatch.DoesNotExist, Stock.DoesNotExist):
        return False

def get_stock_balance(product, warehouse, batch_number=None):
    """
    Returns current stock balance.
    """
    try:
        if batch_number:
            batch = InventoryBatch.objects.get(product=product, batch_number=batch_number, location=warehouse)
            return batch.current_weight
        else:
            from warehouse_v2.models import Stock
            stock = Stock.objects.get(warehouse=warehouse, material=product)
            return stock.quantity
    except (InventoryBatch.DoesNotExist, Stock.DoesNotExist):
        return Decimal('0')
