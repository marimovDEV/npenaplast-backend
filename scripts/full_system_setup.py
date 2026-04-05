import os
import django
import random
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from django.contrib.auth import get_user_model
from warehouse_v2.models import Warehouse, Material, Stock, Supplier, RawMaterialBatch
from sales_v2.models import Customer, Invoice, SaleItem, Delivery
from production_v2.models import Recipe, RecipeItem, Zames, Bunker, BlockProduction, ProductionOrder, ProductionOrderStage
from finance_v2.models import Cashbox, FinancialTransaction, ExpenseCategory

User = get_user_model()

def run_setup():
    print("🚀 Starting Master System Setup...")

    # 1. Warehouses
    warehouses = {}
    for i in range(1, 5):
        w, _ = Warehouse.objects.get_or_create(name=f"Sklad {i}")
        warehouses[i] = w
    print("✅ Warehouses created.")

    # 2. Cashboxes
    cash_names = [("Asosiy Kassa", "CASH"), ("Humo/Uzcard", "CARD"), ("Ipak Yo'li Bank", "BANK")]
    cashboxes = []
    for name, ctype in cash_names:
        cb, _ = Cashbox.objects.get_or_create(name=name, type=ctype)
        if cb.balance == 0:
            cb.balance = Decimal("16000000.00") if ctype == "CASH" else Decimal("17000000.00")
            cb.save()
        cashboxes.append(cb)
    print("✅ Cashboxes initialized.")

    # 3. Products
    categories = {
        'FINISHED': ['Penoplast Blok 1m3', 'Penoplast List 2cm', 'Penoplast List 3cm', 'Penoplast List 5cm', 'Penoplast Granula'],
        'RAW': ['Polistirol (Xom-ashyo)', 'Yelim (Glue)', 'To\'r (Mesh)', 'Bo\'yoq (Paint)', 'Lenta (Tape)'],
        'SEMI': ['Blok (Yarim tayyor)', 'List (Kesilgan)', 'Panel (Pardozlanmagan)', 'Arka (CNC)', 'Ustun (CNC)'],
        'OTHER': ['Karniz Dekor', 'Moldings', 'Siding', 'Termopanel', 'Fasad Element']
    }
    
    product_objs = []
    for cat, names in categories.items():
        for i, name in enumerate(names):
            p, _ = Material.objects.get_or_create(
                name=name,
                defaults={
                    'sku': f"{cat[:2]}-{1000+i}",
                    'category': cat,
                    'unit': 'kg' if cat == 'RAW' else ('m3' if 'Blok' in name else 'dona'),
                    'price': Decimal(random.randint(5000, 50000))
                }
            )
            product_objs.append(p)
            
            # Initial Stock in Sklad 4 for Finished, Sklad 1 for Raw
            target_w = warehouses[4] if cat == 'FINISHED' else warehouses[1]
            Stock.objects.update_or_create(warehouse=target_w, material=p, defaults={'quantity': 500})
    print("✅ Products and Stock initialized.")

    # 4. Customers
    customer_names = [
        "Jalilov Ma'mur", "Xoldorov Sanjar", "Qodirov Baxtiyor", "Saidov Aziz", "Karimova Lola",
        "Abduvohidov Otabek", "Rustamov Dilshod", "G'ulomova Madina", "Xasanov Ilhom", "Sobirov Farruh"
    ]
    customers = []
    for i, name in enumerate(customer_names):
        c, _ = Customer.objects.get_or_create(
            phone=f"99890111223{i}",
            defaults={
                'name': name,
                'address': f"Toshkent shahri, {i+1}-mavze",
                'customer_type': 'RETAIL' if i % 2 == 0 else 'WHOLESALE'
            }
        )
        customers.append(c)
    print("✅ Customers created.")

    # 5. Finance: Expense Categories & Transactions
    exp_cats = ["Ijara", "Oylik", "Soliq", "Kommunal", "Transport"]
    cat_objs = []
    for name in exp_cats:
        cat, _ = ExpenseCategory.objects.get_or_create(name=name)
        cat_objs.append(cat)
        
    admin_user = User.objects.filter(is_superuser=True).first()
    
    for _ in range(10):
        FinancialTransaction.objects.create(
            cashbox=random.choice(cashboxes),
            amount=Decimal(random.randint(100000, 1000000)),
            type='INCOME',
            department='SALES',
            description="Mijozdan to'lov",
            performed_by=admin_user
        )
    for _ in range(5):
        FinancialTransaction.objects.create(
            cashbox=random.choice(cashboxes),
            amount=Decimal(random.randint(50000, 500000)),
            type='EXPENSE',
            category=random.choice(cat_objs),
            department='ADMIN',
            description="Xarajat",
            performed_by=admin_user
        )
    print("✅ Financial transactions created.")

    # 6. Sales (Invoices)
    finished_products = [p for p in product_objs if p.category == 'FINISHED']
    for i in range(10):
        invoice = Invoice.objects.create(
            invoice_number=f"INV-2026-{2000+i}",
            customer=random.choice(customers),
            total_amount=0,
            status='COMPLETED' if i < 8 else 'NEW',
            payment_method=random.choice(['CASH', 'CARD', 'BANK']),
            created_by=admin_user
        )
        
        # Items
        total = 0
        for _ in range(random.randint(1, 3)):
            p = random.choice(finished_products)
            qty = random.randint(5, 20)
            SaleItem.objects.create(
                invoice=invoice,
                product=p,
                quantity=qty,
                price=p.price
            )
            total += p.price * qty
        invoice.total_amount = total
        invoice.save()
    print("✅ Sales data populated.")

    # 7. Production: Bunkers & Process
    for i in range(1, 6):
        Bunker.objects.get_or_create(name=f"Bunker {i}")
        
    # Test Production Order
    finished_p = finished_products[0]
    for i in range(5):
        p_order = ProductionOrder.objects.create(
            order_number=f"PO-{3000+i}",
            product=finished_p,
            quantity=100,
            status='IN_PROGRESS' if i == 0 else 'PENDING',
            priority='HIGH' if i == 0 else 'MEDIUM',
            responsible=admin_user
        )
        # Stages
        stages = ['ZAMES', 'DRYING', 'BUNKER', 'FORMOVKA', 'BLOK', 'CNC', 'DEKOR']
        for seq, stype in enumerate(stages):
            ProductionOrderStage.objects.create(
                order=p_order,
                stage_type=stype,
                sequence=seq,
                status='ACTIVE' if seq == 0 and i == 0 else 'PENDING',
                responsible=admin_user
            )
    print("✅ Production pipeline initialized.")

    print("\n🎉 ALL DONE! System is now fully populated with test data.")

run_setup()
