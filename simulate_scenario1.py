import os
import django
import sys
from django.utils import timezone
from django.db import transaction

# Setup django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from sales_v2.models import Invoice, Customer
from sales_v2.services import create_invoice, transition_invoice_status
from warehouse_v2.models import Warehouse, Material, Stock
from inventory.models import Inventory
from production_v2.models import ProductionOrder, ProductionOrderStage, Bunker
from production_v2.services import start_production_stage, transition_to_next_stage

def simulate_golden_flow():
    print("--- 🚀 Starting Scenario 1: Golden Flow (MTO) ---")
    
    # 0. Get required entities
    customer, _ = Customer.objects.get_or_create(name="SIM-Golden-Customer", defaults={'phone': '+998901234567'})
    product = Material.objects.get(name="TEST-Finished Block 15kg/m3")
    wh1 = Warehouse.objects.filter(name__icontains='Sklad №1').first()
    wh4 = Warehouse.objects.filter(name__icontains='Sklad №4').first()
    
    # 1. Create Invoice (Order for 10 units)
    print("Step 1: Creating Sales Order (Invoice) for 10 blocks...")
    items = [{'product_id': product.id, 'quantity': 10, 'price': 850000}]
    invoice = create_invoice(
        warehouse_id=wh4.id, 
        customer_id=customer.id, 
        items=items
    )
    print(f"   ✔ Invoice created: {invoice.invoice_number}")

    # 2. Confirm Order (Should trigger production)
    print("Step 2: Confirming order to trigger production...")
    invoice = transition_invoice_status(invoice.id, 'CONFIRMED')
    print(f"   ✔ Invoice status: {invoice.status}")
    
    p_order = ProductionOrder.objects.filter(source_order=invoice.invoice_number).first()
    if not p_order:
        print("   ❌ ERROR: ProductionOrder not created!")
        return
    print(f"   ✔ ProductionOrder created: {p_order.order_number}")

    # 3. MES Logic: Execute Stages
    stages = p_order.stages.order_by('sequence')
    print(f"Step 3: Initializing MES execution for {stages.count()} stages...")
    
    for stage in stages:
        print(f"   ---> Executing Stage: {stage.stage_type} ({stage.get_stage_type_display()})")
        
        # Start Stage
        extra_data = {}
        if stage.stage_type == 'ZAMES':
            # Create a Zames model linked to this stage
            from production_v2.models import Zames, Recipe
            recipe = Recipe.objects.get(name="Test 15kg Block Recipe")
            z = Zames.objects.create(
                zames_number=f"Z-{p_order.order_number}",
                recipe=recipe,
                status='IN_PROGRESS',
                operator=p_order.responsible
            )
            # Link to stage
            stage.related_id = z.id
            stage.save()
            print(f"      [Zames object created: {z.zames_number}]")
            
        if stage.stage_type == 'BUNKER':
            bunker = Bunker.objects.filter(is_occupied=False).first()
            if not bunker:
                print("   ❌ ERROR: No free bunkers for simulation!")
                return
            extra_data = {'bunker_id': bunker.id}
            print(f"      [Bunker selected: {bunker.name}]")

        try:
            start_production_stage(stage.id, extra_data=extra_data)
            print(f"      ✔ Stage Started: {stage.status}")
            
            # Transition (Finish) Stage
            # For simulation, Zames items might need to be resolved but start_production_stage handles it
            transition_to_next_stage(stage.id)
            # Re-fetch stage status (actually we re-fetch the instance)
            stage.refresh_from_db()
            print(f"      ✔ Stage Finished: {stage.status} (Finished at {stage.completed_at})")
        except Exception as e:
            print(f"      ❌ ERROR in stage {stage.stage_type}: {e}")
            return

    # 4. Final Verification
    print("Step 4: Post-production verification...")
    invoice.refresh_from_db()
    product_stock = Inventory.objects.filter(product=product, warehouse=wh4).first()
    
    print(f"   ✔ Final Invoice Status: {invoice.status} (Expected: READY)")
    if product_stock:
        print(f"   ✔ Final Stock in Sklad 4: {product_stock.quantity} (Expected: 10)")
    else:
        print(f"   ❌ ERROR: Stock record missing in Sklad 4!")

    if invoice.status == 'READY' and product_stock and product_stock.quantity >= 10:
        print("\n--- ✅ SCENARIO 1 COMPLETE: GOLDEN FLOW SUCCESSFUL ---")
    else:
        print("\n--- ❌ SCENARIO 1 FAILED: Incomplete fulfillment ---")

if __name__ == "__main__":
    simulate_golden_flow()
