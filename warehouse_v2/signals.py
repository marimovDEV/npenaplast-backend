from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import RawMaterialBatch, WarehouseTransfer, Stock

@receiver(post_save, sender=RawMaterialBatch)
def update_stock_on_batch_creation(sender, instance, created, **kwargs):
    if created:
        # Assuming Sklad 1 is the default for new batches if not specified
        # In a real system, we'd have a warehouse field in the Batch model
        # For now, we'll try to find a warehouse named "Sklad 1"
        from .models import Warehouse
        warehouse, _ = Warehouse.objects.get_or_create(name='Sklad 1 (Xom Ashyo)')
        stock, _ = Stock.objects.get_or_create(warehouse=warehouse, material=instance.material)
        stock.quantity += instance.quantity_kg
        stock.save()

@receiver(post_save, sender=WarehouseTransfer)
def update_stock_on_transfer(sender, instance, created, **kwargs):
    if created:
        # 1. Decrease from source
        from_stock, _ = Stock.objects.get_or_create(warehouse=instance.from_warehouse, material=instance.material)
        if from_stock.quantity < instance.quantity:
            # In a production system, we'd raise a validation error before saving
            # Since this is a post_save signal, we just adjust it
            pass
        from_stock.quantity -= instance.quantity
        from_stock.save()

        # 2. Increase in destination
        to_stock, _ = Stock.objects.get_or_create(warehouse=instance.to_warehouse, material=instance.material)
        to_stock.quantity += instance.quantity
        to_stock.save()
