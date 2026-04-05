import os
import django
import threading
import time
from decimal import Decimal
import uuid

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from warehouse_v2.models import Material, Stock, Warehouse
from production_v2.models import Zames, Recipe
from django.db import transaction
from django.utils import timezone

def test_mathematical_balance():
    print("--- 🧪 Testing Mathematical Balance ---")
    try:
        # 1. Get initial stock for a random material
        material = Material.objects.filter(name__icontains='granula').first()
        if not material:
            print("❌ Material 'granula' not found.")
            return

        sklad1 = Warehouse.objects.filter(name__icontains='Sklad 1').first()
        if not sklad1:
            print("❌ 'Sklad 1' not found.")
            return

        stock_obj, created = Stock.objects.get_or_create(warehouse=sklad1, material=material)
        initial_stock = stock_obj.quantity
        
        print(f"Material: {material.name}, Initial Stock: {initial_stock}")
        
        # 2. Simulate a usage
        usage_qty = 50.0 # Match FloatField
        with transaction.atomic():
            stock = Stock.objects.get(warehouse=sklad1, material=material)
            stock.quantity -= usage_qty
            stock.save()
            
            # Create a mock zames record
            recipe = Recipe.objects.first()
            if not recipe:
                recipe = Recipe.objects.create(name="Default Recipe")
            
            Zames.objects.create(
                zames_number=f"TEST-{uuid.uuid4().hex[:6]}",
                recipe=recipe,
                machine_id="M1",
                status='DONE',
                start_time=timezone.now(),
                end_time=timezone.now(),
                input_weight=usage_qty
            )
            
        new_stock = Stock.objects.get(warehouse=sklad1, material=material).quantity
        print(f"New Stock: {new_stock}")
        
        if initial_stock - usage_qty == new_stock:
            print("✅ TEST PASSED: Stocks update correctly.")
        else:
            print("❌ TEST FAILED: Stock mismatch!")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

def simulate_concurrent_zames(user_id):
    try:
        with transaction.atomic():
            recipe = Recipe.objects.first()
            z = Zames.objects.create(
                zames_number=f"STRESS-{uuid.uuid4().hex[:6]}",
                recipe=recipe,
                machine_id=str(user_id),
                status='PENDING',
                start_time=timezone.now()
            )
            print(f"User {user_id} created Zames {z.id}")
            time.sleep(0.2) # Simulate processing
            z.status = 'DONE'
            z.save()
    except Exception as e:
        print(f"User {user_id} FAILED: {e}")

def test_sqlite_concurrency():
    print("\n--- ⚡ Testing SQLite Concurrency (Stress Test) ---")
    threads = []
    for i in range(5):
        t = threading.Thread(target=simulate_concurrent_zames, args=(i+200,))
        threads.append(t)
        
    for t in threads:
        t.start()
        
    for t in threads:
        t.join()
    print("✅ Stress test completed. Check above for errors.")

if __name__ == "__main__":
    test_mathematical_balance()
    test_sqlite_concurrency()
