from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from inventory.models import Inventory

from .models import Material, RawMaterialBatch, Stock, Supplier, Warehouse


class WarehouseRoleMatrixTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.omborchi = User.objects.create_user(
            username='warehouse-user',
            password='testpass123',
            full_name='Warehouse User',
            phone='+998900003001',
            role='Omborchi',
        )
        self.sales = User.objects.create_user(
            username='sales-user',
            password='testpass123',
            full_name='Sales User',
            phone='+998900003002',
            role='Sotuv menejeri',
        )
        self.sklad1 = Warehouse.objects.create(name='Sklad №1')
        self.sklad2 = Warehouse.objects.create(name='Sklad №2')
        self.omborchi.assigned_warehouses.add(self.sklad1)
        self.material = Material.objects.create(name='EPS 80', unit='kg', category='RAW', price=Decimal('1000'))
        self.supplier = Supplier.objects.create(name='Supplier A')
        self.batch = RawMaterialBatch.objects.create(
            invoice_number='INV-WH-1',
            supplier=self.supplier,
            quantity_kg=100,
            remaining_quantity=100,
            reserved_quantity=0,
            batch_number='RAW-WH-001',
            responsible_user=self.omborchi,
            material=self.material,
            status='IN_STOCK',
        )
        Stock.objects.create(warehouse=self.sklad1, material=self.material, quantity=100)
        Inventory.objects.create(product=self.material, warehouse=self.sklad1, quantity=100, batch_number='RAW-WH-001')

    def test_omborchi_only_sees_assigned_warehouses(self):
        Warehouse.objects.create(name='Sklad №3')
        self.client.force_authenticate(self.omborchi)

        warehouses_response = self.client.get('/api/warehouses/')
        stocks_response = self.client.get('/api/stocks/')

        self.assertEqual(warehouses_response.status_code, 200)
        self.assertEqual(len(warehouses_response.data), 1)
        self.assertEqual(warehouses_response.data[0]['name'], 'Sklad №1')
        self.assertEqual(stocks_response.status_code, 200)
        self.assertEqual(len(stocks_response.data), 1)
        self.assertEqual(stocks_response.data[0]['warehouse_name'], 'Sklad №1')

    def test_sales_cannot_create_raw_material_batch(self):
        self.client.force_authenticate(self.sales)
        response = self.client.post('/api/batches/', {
            'invoice_number': 'INV-WH-2',
            'supplier': self.supplier.id,
            'quantity_kg': 10,
            'remaining_quantity': 10,
            'batch_number': 'RAW-WH-002',
            'material': self.material.id,
            'status': 'IN_STOCK',
        })
        self.assertEqual(response.status_code, 403)

    def test_inventory_compatibility_is_limited_to_assigned_warehouse(self):
        sklad3 = Warehouse.objects.create(name='Sklad №3')
        Stock.objects.create(warehouse=sklad3, material=self.material, quantity=55)

        self.client.force_authenticate(self.omborchi)
        response = self.client.get('/api/inventory/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['warehouse'], self.sklad1.id)

    def test_products_compatibility_respects_type_filter(self):
        finished = Material.objects.create(name='Decor Panel', unit='dona', category='FINISHED', price=Decimal('500'))
        Stock.objects.create(warehouse=self.sklad1, material=finished, quantity=5)

        self.client.force_authenticate(self.omborchi)
        response = self.client.get('/api/products/?type=RAW')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['category'], 'RAW')
