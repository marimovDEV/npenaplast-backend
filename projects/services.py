from django.db import transaction
from decimal import Decimal
from .models import ConstructionProject, ProjectSupply
from inventory.services import update_inventory
from finance.services import record_double_entry

def create_project(name, leader=None, budget=0, location=''):
    return ConstructionProject.objects.create(
        name=name,
        leader=leader,
        budget=budget,
        location=location
    )

def add_project_supply(project_id, product, warehouse, quantity, user=None, notes=''):
    """
    Consumes material from inventory for an internal construction project.
    Debit: Project Expense, Credit: Inventory.
    """
    with transaction.atomic():
        project = ConstructionProject.objects.get(id=project_id)
        
        # 1. Deduct Inventory (Physical)
        # Using the new update_inventory which handles InventoryBatch
        batch = update_inventory(
            product=product,
            warehouse=warehouse,
            qty=-quantity,
            user=user,
            notes=f"Project Supply: {project.name}"
        )
        
        # 2. Record Project Supply
        supply = ProjectSupply.objects.create(
            project=project,
            product=product,
            quantity=quantity,
            delivered_by=user,
            notes=notes
        )
        
        # 3. Finance (Accounting)
        # Debit: Production/Project Expense (9910), Credit: WIP/Finished Goods (2020/2030)
        # We find the source account based on warehouse or product category
        source_acc = '2030' if product.category == 'FINISHED' else '2020'
        
        record_double_entry(
            description=f"Loyiha ta'minoti: {project.name} - {product.name}",
            entries=[
                {'account_code': '9910', 'debit': Decimal('0'), 'credit': Decimal('0')}, # Expense
                {'account_code': source_acc, 'debit': Decimal('0'), 'credit': Decimal('0')}, # Asset Move
            ],
            reference=f"PROJ-{project.id}-{supply.id}",
            user=user
        )
        
        return supply
