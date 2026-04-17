import os
import django
import random
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from warehouse_v2.models import Warehouse, Material, Stock, RawMaterialBatch
from products.models import Product
from products.models import ProductionTask
from production_v2.models import Recipe, RecipeItem, ProductionOrder, Bunker
from sales_v2.models import Customer, Invoice
from finance_v2.models import Cashbox, ClientBalance
from django.contrib.auth import get_user_model

User = get_user_model()

def seed_data():
    print("🚀 Penoplast ERP Enterprise Seeding Boshlanmoqda...")
    
    # 1. Users
    admin, _ = User.objects.get_or_create(username='admin', defaults={'is_superuser': True, 'is_staff': True})
    admin.set_password('admin123')
    admin.save()
    
    # 2. Warehouses
    wh1, _ = Warehouse.objects.get_or_create(name='Sklad №1 (Xom Ashyo)')
    wh2, _ = Warehouse.objects.get_or_create(name='Sklad №2 (Bloklar)')
    wh3, _ = Warehouse.objects.get_or_create(name='Sklad №3 (Ichki)')
    wh4, _ = Warehouse.objects.get_or_create(name='Sklad №4 (Tayyor Mahsulot)')
    
    # 3. Materials & Products
    granula, _ = Material.objects.get_or_create(name='Granula EPS (Penoplast)', defaults={'category': 'RAW', 'unit': 'kg', 'price': 15000})
    glue, _ = Material.objects.get_or_create(name='Yelim (Glue)', defaults={'category': 'RAW', 'unit': 'kg', 'price': 8000})
    
    # Finished products are also Materials in warehouse_v2 (Phase 4 integration)
    block_prod, _ = Material.objects.get_or_create(name='Styrofoam Block 20kg/m3', defaults={'category': 'FINISHED', 'unit': 'm3', 'price': 450000})
    dekor_pane, _ = Material.objects.get_or_create(name='Dekorativ Panel "Gofra"', defaults={'category': 'FINISHED', 'unit': 'stk', 'price': 25000})
    
    # 4. Stocks
    Stock.objects.get_or_create(warehouse=wh1, material=granula, defaults={'quantity': 5000})
    Stock.objects.get_or_create(warehouse=wh1, material=glue, defaults={'quantity': 1000})
    
    # 5. Recipes
    recipe, _ = Recipe.objects.get_or_create(name='Standard Block Recipe', product=block_prod, defaults={'is_active': True})
    RecipeItem.objects.get_or_create(recipe=recipe, material=granula, defaults={'quantity': 20.5}) # 20.5kg for 1m3
    
    # 6. Bunkers
    for i in range(1, 6):
        Bunker.objects.get_or_create(name=f"Bunker #{i}", defaults={'is_occupied': False})
    
    # 7. Customers
    c1, _ = Customer.objects.get_or_create(name='Real STROY LLC', defaults={'phone': '+998901234567', 'segment': 'VIP', 'credit_limit': 50000000})
    c2, _ = Customer.objects.get_or_create(name='Marat Aka (Diller)', defaults={'phone': '+998911112233', 'segment': 'REGULAR', 'credit_limit': 5000000})
    
    # 8. Cashbox
    Cashbox.objects.get_or_create(name='Asosiy Kassa (Naqd)', defaults={'type': 'CASH', 'is_active': True})
    
    # 9. Initial Balances
    ClientBalance.objects.get_or_create(customer=c1, defaults={'total_debt': 12000000, 'overdue_debt': 0})
    
    print("✅ Seeding tugadi! Tizim endi ishlatishga tayyor.")

if __name__ == "__main__":
    seed_data()
