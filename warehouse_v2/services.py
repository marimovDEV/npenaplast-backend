from django.db import transaction
from django.db.models import F, Sum
from .models import RawMaterialBatch, Stock

def consume_material_fifo(material, quantity, warehouse, user=None):
    """
    Consumes material from the oldest available batches in the given warehouse.
    Updates remaining_quantity and batch status.
    """
    with transaction.atomic():
        # Find active batches for this material in this warehouse, ordered by date (FIFO)
        # Note: In our current model, batches aren't strictly 'in' a warehouse via FK, 
        # but for Sklad 1 (Raw), we assume all RawMaterialBatch belong there.
        # If we had multiple raw warehouses, we'd filter by warehouse.
        batches = RawMaterialBatch.objects.filter(
            material=material,
            remaining_quantity__gt=0,
            status='IN_STOCK'
        ).order_by('date', 'id')

        total_available = batches.aggregate(total=Sum('remaining_quantity'))['total'] or 0
        if total_available < quantity:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(f"Yetersiz qoldiq. So'ralgan: {quantity}, Mavjud: {total_available}")

        rem_to_consume = quantity
        consumed_details = []

        for batch in batches:
            if rem_to_consume <= 0:
                break
            
            take = min(batch.remaining_quantity, rem_to_consume)
            batch.remaining_quantity = F('remaining_quantity') - take
            batch.save()
            batch.refresh_from_db()

            if batch.remaining_quantity <= 0:
                batch.status = 'DEPLETED'
                batch.save()
            
            consumed_details.append({
                'batch_number': batch.batch_number,
                'quantity': take
            })
            rem_to_consume -= take

        # Update aggregate Stock
        stock, _ = Stock.objects.get_or_create(warehouse=warehouse, material=material)
        stock.quantity = F('quantity') - quantity
        stock.save()

        return consumed_details

def reserve_material_fifo(material, quantity, document):
    """
    Finds available stock (remaining - reserved) via FIFO and reserves it for the given document.
    """
    from .models import BatchReservation
    with transaction.atomic():
        # Only active batches with available stock
        batches = RawMaterialBatch.objects.filter(
            material=material,
            remaining_quantity__gt=F('reserved_quantity'),
            status='IN_STOCK'
        ).order_by('date', 'id')

        # Calculate total available across all batches
        # (Remaining - Reserved)
        available = batches.aggregate(
            total=Sum(F('remaining_quantity') - F('reserved_quantity'))
        )['total'] or 0

        if available < quantity:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(f"Yetarli bo'sh qoldiq yo'q. So'ralgan: {quantity}, Bo'sh: {available}")

        rem_to_reserve = quantity
        for batch in batches:
            if rem_to_reserve <= 0: break
            
            can_take = batch.remaining_quantity - batch.reserved_quantity
            take = min(can_take, rem_to_reserve)
            
            BatchReservation.objects.create(
                document=document,
                batch=batch,
                quantity=take
            )
            
            batch.reserved_quantity = F('reserved_quantity') + take
            batch.save()
            rem_to_reserve -= take

def release_reservation(document):
    """
    Clears all reservations for a document and restores the batch reserved_quantity.
    Typically used on CANCEL or prior to physical deduction.
    """
    with transaction.atomic():
        for res in document.reservations.all():
            batch = res.batch
            batch.reserved_quantity = F('reserved_quantity') - res.quantity
            batch.save()
            res.delete()

def fulfill_reservation(document, warehouse, user=None):
    """
    Converts reservations into physical deductions. 
    Decreases remaining_quantity and clears reserved_quantity.
    """
    from transactions.services import create_transaction
    with transaction.atomic():
        total_deducted = 0
        for res in document.reservations.all():
            batch = res.batch
            batch.remaining_quantity = F('remaining_quantity') - res.quantity
            batch.reserved_quantity = F('reserved_quantity') - res.quantity
            batch.save()
            batch.refresh_from_db()
            
            if batch.remaining_quantity <= 0:
                batch.status = 'DEPLETED'
                batch.save()

            create_transaction(
                product=batch.material,
                from_wh=warehouse,
                to_wh=None,
                qty=res.quantity,
                trans_type='OUT',
                batch=batch,
                batch_number=batch.batch_number,
                document=document,
                user=user
            )
            total_deducted += res.quantity
            res.delete()
        
        # Aggregate stock is already adjusted inside create_transaction -> update_inventory.
