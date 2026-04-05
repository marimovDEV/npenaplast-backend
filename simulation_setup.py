import os
import django
import sys

# Setup django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from warehouse_v2.models import Warehouse, Material, RawMaterialBatch
from inventory.models import Inventory
from production_v2.models import Recipe, RecipeItem, Bunker
from django.utils import timezone

def run_simulation_setup():
    print("--- Starting Factory Simulation Setup ---")
    
    # 1. Setup Warehouses (using existing ones if possible)
    wh1 = Warehouse.objects.filter(name__icontains='Sklad №1').first() or Warehouse.objects.create(name="Sklad №1 (Raw)")
    wh2 = Warehouse.objects.filter(name__icontains='Sklad №2').first() or Warehouse.objects.create(name="Sklad №2 (Semi)")
    wh3 = Warehouse.objects.filter(name__icontains='Sklad №3').first() or Warehouse.objects.create(name="Sklad №3 (Bunkers)")
    wh4 = Warehouse.objects.filter(name__icontains='Sklad №4').first() or Warehouse.objects.create(name="Sklad №4 (Finished)")
    print(f"Warehouses initialized: {wh1.name}, {wh2.name}, {wh3.name}, {wh4.name}")

    # 2. Setup Materials
    mat_raw, _ = Material.objects.get_or_create(
        name="TEST-EPS Beads (Original)",
        category="RAW",
        defaults={'unit': 'kg', 'sku': 'SIM-RAW-001', 'price': 12000}
    )
    mat_semi, _ = Material.objects.get_or_create(
        name="TEST-Expanded EPS",
        category="SEMI",
        defaults={'unit': 'kg', 'sku': 'SIM-SEMI-001', 'price': 15000}
    )
    mat_finished, _ = Material.objects.get_or_create(
        name="TEST-Finished Block 15kg/m3",
        category="FINISHED",
        defaults={'unit': 'm3', 'sku': 'SIM-FIN-001', 'price': 850000}
    )
    print(f"Materials initialized: {mat_raw}, {mat_semi}, {mat_finished}")

    # 3. Setup Recipe for Finished Block
    recipe, created = Recipe.objects.get_or_create(
        product=mat_finished,
        name="Test 15kg Block Recipe",
        defaults={'density': 15.0, 'is_active': True}
    )
    if created:
        RecipeItem.objects.create(recipe=recipe, material=mat_raw, quantity=1.02) # 1.02kg per whatever unit
        print(f"Recipe created: {recipe}")
    else:
        print(f"Recipe already exists: {recipe}")

    # 4. Setup Initial Stock (Sklad 1)
    batch_no = "SIM-RAW-BATCH-001"
    batch, b_created = RawMaterialBatch.objects.get_or_create(
        batch_number=batch_no,
        defaults={
            'material': mat_raw,
            'quantity_kg': 5000,
            'remaining_quantity': 5000,
            'status': 'IN_STOCK',
            'invoice_number': 'SIM-INV-001',
            'date': timezone.now().date()
        }
    )
    
    inv, _ = Inventory.objects.get_or_create(
        product=mat_raw,
        warehouse=wh1,
        batch_number=batch_no,
        defaults={'quantity': 5000}
    )
    print(f"Initial Stock set: 5000kg Beads in Sklad 1 (Batch: {batch_no})")

    # 5. Ensure Bunkers exist
    for i in range(1, 5):
        Bunker.objects.get_or_create(
            name=f"Bunker №{i}",
            defaults={'is_occupied': False}
        )
    print("Bunkers 1-4 initialized and ready.")

    print("--- Simulation Setup Complete ---")

if __name__ == "__main__":
    run_simulation_setup()
