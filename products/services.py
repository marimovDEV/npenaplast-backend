from django.db import transaction
from django.core.exceptions import ValidationError
from inventory.services import update_inventory
from transactions.services import create_transaction
from warehouse.models import Warehouse
from .models import ProductionTask

def advance_task_stage(task, next_stage, user=None):
    """
    Advances a production task to the next stage and handles inventory transformations.
    """
    with transaction.atomic():
        current_stage = task.stage
        task.stage = next_stage
        
        # Logic for specific stage transitions
        if current_stage == 'CNC' and next_stage == 'FINISHING':
            # Example: Move from CNC shop to Finishing Shop
            # We assume the CNC job consumed a block and now it's a "semi-finished" item
            pass 

        task.save()
        return task

def complete_production_task(task, target_warehouse_name="Sklad №4", user=None):
    """
    Finalizes a production task and moves the finished product to the target warehouse.
    """
    with transaction.atomic():
        if task.is_completed:
            return task
            
        target_wh = Warehouse.objects.get(name=target_warehouse_name)
        
        # Create inventory entry for the finished product
        if task.product:
            create_transaction(
                product=task.product,
                from_wh=None, # From production
                to_wh=target_wh,
                qty=1, # Default to 1 for simplified task logic
                trans_type='PRODUCTION',
                batch_number=f"PROD-{task.id}"
            )

        task.is_completed = True
        task.save()
        return task
