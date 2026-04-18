import os
import django
import random
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from accounts.models import User
from warehouse_v2.models import Warehouse, Material, Supplier, Stock
from production_v2.models import Zames, BlockProduction, DryingProcess
from sales_v2.models import Customer

def run():
    print("Setting up Yuksar ERP v2...")
    
    # 1. Warehouses
    sklad1, _ = Warehouse.objects.get_or_create(name='Sklad 1 (Xom Ashyo)')
    sklad2, _ = Warehouse.objects.get_or_create(name='Sklad 2 (Tayyor Bloklar)')
    sklad4, _ = Warehouse.objects.get_or_create(name='Sklad 4 (Tayyor Mahsulotlar)')
    
    # 2. Materials
    m1, _ = Material.objects.get_or_create(name='Granula EPS', unit='kg')
    m2, _ = Material.objects.get_or_create(name='Blok 15kg', unit='dona')
    m3, _ = Material.objects.get_or_create(name='Korniz K-1', unit='dona')
    
    # 3. Suppliers
    sup1, _ = Supplier.objects.get_or_create(name='Global Chemical LLC')
    
    # 4. Users
    admin_user, _ = User.objects.get_or_create(
        username='admin', 
        defaults={
            'email': 'admin@example.com', 
            'full_name': 'System Admin', 
            'role': 'Bosh Admin',
            'assigned_warehouses': '*'
        }
    )
    admin_user.set_password('admin')
    admin_user.save()
    
    # 5. Stocks
    Stock.objects.get_or_create(warehouse=sklad1, material=m1, defaults={'quantity': 5000})
    Stock.objects.get_or_create(warehouse=sklad4, material=m3, defaults={'quantity': 250})
    
    # 6. Production Chain
    if not Zames.objects.exists():
        z = Zames.objects.create(
            zames_number='Z-101',
            raw_material_weight=100.0,
            expanded_weight=98.0,
            dried_weight=95.0,
            operator=admin_user
        )
        bp = BlockProduction.objects.create(
            zames=z,
            form_number='F-01',
            block_count=10
        )
        DryingProcess.objects.create(
            block_production=bp,
            start_time=timezone.now() - timedelta(hours=5)
        )
    
    print("Setup completed successfully.")

if __name__ == '__main__':
    run()
