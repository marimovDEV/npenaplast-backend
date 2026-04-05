from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import Inventory

def update_inventory(product, warehouse, qty, batch_number=None):
    """
    Updates or creates an inventory record for a specific product, warehouse, and batch.
    """
    with transaction.atomic():
        # Update Legacy Inventory
        obj, created = Inventory.objects.get_or_create(
            product=product,
            warehouse=warehouse,
            batch_number=batch_number,
            defaults={'quantity': 0}
        )
        
        if obj.quantity + qty < 0:
            raise ValidationError(f"Yetersiz qoldiq: {obj.product.name} @ {obj.warehouse.name}. Mavjud: {obj.quantity}, Talab: {abs(qty)}")
        
        obj.quantity += qty
        obj.save()

        # Update V2 Stock (Aggregate)
        from warehouse_v2.models import Stock
        stock_obj, _ = Stock.objects.get_or_create(
            warehouse_id=warehouse.id,
            material_id=product.id,
            defaults={'quantity': 0}
        )
        stock_obj.quantity += qty
        stock_obj.save()

        return obj

def check_stock(product, warehouse, qty, batch_number=None):
    """
    Checks if enough stock exists.
    """
    try:
        inv = Inventory.objects.get(product=product, warehouse=warehouse, batch_number=batch_number)
        return inv.quantity >= qty
    except Inventory.DoesNotExist:
        return False

def get_stock_balance(product, warehouse, batch_number=None):
    """
    Returns current stock balance.
    """
    try:
        inv = Inventory.objects.get(product=product, warehouse=warehouse, batch_number=batch_number)
        return inv.quantity
    except Inventory.DoesNotExist:
        return 0
