from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import RawMaterialBatch, WarehouseTransfer, Stock

# Enterprise Hardening: Automatic signals that modify state in a "hidden" way 
# are discouraged in high-integrity systems. 
# We are moving this logic to the Service Layer (InventoryService).

@receiver(post_save, sender=RawMaterialBatch)
def update_stock_on_batch_creation(sender, instance, created, **kwargs):
    # Log logic only or keep disabled to ensure Service Layer is the only entry point
    pass

@receiver(post_save, sender=WarehouseTransfer)
def update_stock_on_transfer(sender, instance, created, **kwargs):
    # Log logic only or keep disabled to ensure Service Layer is the only entry point
    pass
