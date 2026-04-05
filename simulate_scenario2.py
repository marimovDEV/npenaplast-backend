import os
import django
import sys
from django.db import transaction
from django.utils import timezone

# Setup django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from production_v2.models import ProductionOrder, ProductionOrderStage, Bunker
from production_v2.services import start_production_stage, force_release_bunker, create_production_order
from warehouse_v2.models import Material
from rest_framework.exceptions import ValidationError

def simulate_chaos():
    print("--- 🌪️ Starting Scenario 2: Chaos & Resource Integrity ---")
    
    # Clean slate: Close any active Zames to allow WIP testing
    from production_v2.models import ProductionOrderStage
    ProductionOrderStage.objects.filter(stage_type='ZAMES', status='ACTIVE').update(status='DONE')
    print("   [Clean-up] All pre-existing active Zames cleared.")
    
    product = Material.objects.get(name="TEST-Finished Block 15kg/m3")
    
    # --- Part A: WIP Limit Test (Max 2 Zames ACTIVE) ---
    print("\nPart A: Testing WIP Limits (Max 2 Zames concurrently)...")
    
    # 1. Ensure we have 3 independent orders
    orders = []
    ts = int(timezone.now().timestamp())
    for i in range(3):
        order = create_production_order(product, 10, order_number=f"CHAOS-WIP-{ts}-{i}")
        orders.append(order)
        print(f"   Created order: {order.order_number}")

    # 2. Start Zames for first 2
    for i in range(2):
        z_stage = orders[i].stages.get(stage_type='ZAMES')
        start_production_stage(z_stage.id)
        print(f"   ✔ Started Zames for {orders[i].order_number} (Status: ACTIVE)")

    # 3. Attempt starting Zames for the 3rd one
    print("   Attempting to start 3rd Zames (Expect WIP Limit error)...")
    z_stage_3 = orders[2].stages.get(stage_type='ZAMES')
    try:
        start_production_stage(z_stage_3.id)
        print("   ❌ FAIL: System allowed 3 active Zames!")
    except ValidationError as e:
        print(f"   ✅ PASS: System blocked 3rd Zames: {e}")

    # --- Part B: Resource Deadlock Test (Bunker Locking) ---
    print("\nPart B: Testing Bunker Locking...")
    
    # 1. Prepare Order 0 for Bunker (Zames -> Drying -> Bunker)
    print("   Preparing Order 0 (Completing Zames & Drying)...")
    z_stage_0 = orders[0].stages.get(stage_type='ZAMES')
    d_stage_0 = orders[0].stages.get(stage_type='DRYING')
    # Zames already started in Part A for orders[0]
    from production_v2.services import transition_to_next_stage
    transition_to_next_stage(z_stage_0.id) # Finish Zames, starts Drying
    transition_to_next_stage(d_stage_0.id) # Finish Drying, starts Bunker

    b1 = Bunker.objects.get(name="Bunker №1")
    # Reset it first just in case
    b1.is_occupied = False
    b1.save()
    
    b_stage_0 = orders[0].stages.get(stage_type='BUNKER')
    from production_v2.models import Zames
    # Need a real zames for the loading logic
    dummy_z = Zames.objects.create(zames_number=f"Z-CHAOS-{ts}", status='DONE')
    start_production_stage(b_stage_0.id, extra_data={'bunker_id': b1.id, 'zames_id': dummy_z.id})
    print(f"   ✔ Bunker №1 occupied for {orders[0].order_number}")

    # 2. Prepare Order 1 for Bunker
    print("   Preparing Order 1 (Completing Zames & Drying)...")
    z_stage_1 = orders[1].stages.get(stage_type='ZAMES')
    d_stage_1 = orders[1].stages.get(stage_type='DRYING')
    # Zames already started in Part A for orders[1]
    transition_to_next_stage(z_stage_1.id)
    transition_to_next_stage(d_stage_1.id)

    print(f"   Attempting to occupy occupied {b1.name} for {orders[1].order_number}...")
    b_stage_1 = orders[1].stages.get(stage_type='BUNKER')
    try:
        start_production_stage(b_stage_1.id, extra_data={'bunker_id': b1.id, 'zames_id': dummy_z.id})
        print("   ❌ FAIL: System allowed double-occupancy of Bunker!")
    except ValidationError as e:
        print(f"   ✅ PASS: System blocked double-occupancy: {e}")

    # --- Part C: Admin Force Release ---
    print("\nPart C: Testing Admin Force-Release...")
    
    print(f"   [Admin] Force releasing {b1.name}...")
    force_release_bunker(b1.id)
    b1.refresh_from_db()
    
    if not b1.is_occupied:
        print(f"   ✔ Bunker {b1.name} is now FREE.")
        print(f"   Attempting to re-occupy {b1.name} for {orders[1].order_number}...")
        try:
            start_production_stage(b_stage_1.id, extra_data={'bunker_id': b1.id, 'zames_id': 999})
            print(f"   ✅ PASS: Bunker successfully re-occupied after admin release.")
        except Exception as e:
            print(f"   ❌ FAIL: Could not occupy even after release: {e}")
    else:
        print(f"   ❌ FAIL: Bunker still occupied after force_release!")

    print("\n--- ✅ SCENARIO 2 COMPLETE: CHAOS TESTS SUCCESSFUL ---")

if __name__ == "__main__":
    simulate_chaos()
