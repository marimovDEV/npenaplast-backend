from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from inventory.models import Inventory
from sales_v2.models import Customer
from warehouse_v2.models import BatchReservation, Material, RawMaterialBatch, Stock, Supplier, Warehouse

from .models import Document, DocumentDelivery, DocumentItem
from .services import complete_document, confirm_document


class DocumentFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='doc-admin',
            password='testpass123',
            full_name='Doc Admin',
            phone='+998900001001',
            role='Bosh Admin',
        )
        self.courier = User.objects.create_user(
            username='doc-courier',
            password='testpass123',
            full_name='Doc Courier',
            phone='+998900001002',
            role='Kuryer',
        )
        self.outsider = User.objects.create_user(
            username='doc-outsider',
            password='testpass123',
            full_name='Doc Outsider',
            phone='+998900001004',
            role='Buxgalter',
        )
        self.customer = Customer.objects.create(
            name='Doc Client',
            phone='+998900001003',
        )
        self.sklad1 = Warehouse.objects.create(name='Sklad №1')
        self.sklad4 = Warehouse.objects.create(name='Sklad №4')
        self.raw_material = Material.objects.create(name='EPS 70', unit='kg', category='RAW', price=Decimal('1000'))
        self.finished = Material.objects.create(name='Panel', unit='dona', category='FINISHED', price=Decimal('50000'))

    def test_document_qr_content_uses_document_number(self):
        document = Document.objects.create(
            type='HISOB_FAKTURA_KIRIM',
            number='INV-IN-TEST',
            to_warehouse=self.sklad1,
            created_by=self.admin,
        )
        delivery = DocumentDelivery.objects.create(document=document, courier=self.courier)

        self.assertEqual(document.qr_content, 'DOC:INV-IN-TEST')
        self.assertEqual(delivery.qr_content, 'DOC:INV-IN-TEST')

    def test_document_list_supports_qr_and_courier_filters(self):
        target_document = Document.objects.create(
            type='ICHKI_YUK_XATI',
            number='INT-0001',
            from_warehouse=self.sklad4,
            to_warehouse=self.sklad1,
            created_by=self.admin,
        )
        DocumentDelivery.objects.create(document=target_document, courier=self.courier)
        Document.objects.create(
            type='ICHKI_YUK_XATI',
            number='INT-0002',
            from_warehouse=self.sklad4,
            to_warehouse=self.sklad1,
            created_by=self.admin,
        )

        self.client.force_authenticate(self.admin)
        courier_response = self.client.get(f'/api/documents/?courier_id={self.courier.id}')
        qr_response = self.client.get('/api/documents/?qr_code=DOC:INT-0001')

        self.assertEqual(courier_response.status_code, 200)
        self.assertEqual(len(courier_response.data), 1)
        self.assertEqual(courier_response.data[0]['number'], 'INT-0001')
        self.assertEqual(qr_response.status_code, 200)
        self.assertEqual(len(qr_response.data), 1)
        self.assertEqual(qr_response.data[0]['number'], 'INT-0001')

    def test_courier_only_sees_documents_assigned_to_them(self):
        assigned_document = Document.objects.create(
            type='ICHKI_YUK_XATI',
            number='INT-COURIER-1',
            from_warehouse=self.sklad4,
            to_warehouse=self.sklad1,
            created_by=self.admin,
        )
        hidden_document = Document.objects.create(
            type='ICHKI_YUK_XATI',
            number='INT-COURIER-2',
            from_warehouse=self.sklad4,
            to_warehouse=self.sklad1,
            created_by=self.admin,
        )
        DocumentDelivery.objects.create(document=assigned_document, courier=self.courier)
        other_courier = User.objects.create_user(
            username='doc-courier-2',
            password='testpass123',
            full_name='Doc Courier 2',
            phone='+998900001005',
            role='Kuryer',
        )
        DocumentDelivery.objects.create(document=hidden_document, courier=other_courier)

        self.client.force_authenticate(self.courier)
        response = self.client.get('/api/documents/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['number'], 'INT-COURIER-1')

    def test_document_access_is_forbidden_for_unrelated_role(self):
        self.client.force_authenticate(self.outsider)
        response = self.client.get('/api/documents/')
        self.assertEqual(response.status_code, 403)

    def test_complete_sales_document_deducts_exact_batch(self):
        Inventory.objects.create(
            product=self.finished,
            warehouse=self.sklad4,
            quantity=5,
            reserved_quantity=0,
            batch_number='FIN-001',
        )
        Stock.objects.create(warehouse=self.sklad4, material=self.finished, quantity=5)
        document = Document.objects.create(
            type='HISOB_FAKTURA_CHIQIM',
            number='ORD-TEST',
            from_warehouse=self.sklad4,
            client=self.customer,
            created_by=self.admin,
        )
        DocumentItem.objects.create(
            document=document,
            product=self.finished,
            quantity=2,
            price_at_moment=Decimal('50000'),
            batch_number='FIN-001',
        )

        complete_document(document, user=self.admin)

        document.refresh_from_db()
        inventory = Inventory.objects.get(product=self.finished, warehouse=self.sklad4, batch_number='FIN-001')
        stock = Stock.objects.get(warehouse=self.sklad4, material=self.finished)
        self.assertEqual(document.status, 'DONE')
        self.assertEqual(inventory.quantity, 3)
        self.assertEqual(stock.quantity, 3)

    def test_fulfilling_sklad1_reservation_does_not_double_decrease_stock(self):
        supplier = Supplier.objects.create(name='Supplier 1')
        RawMaterialBatch.objects.create(
            invoice_number='INV-001',
            supplier=supplier,
            quantity_kg=100,
            remaining_quantity=100,
            reserved_quantity=0,
            batch_number='RAW-001',
            responsible_user=self.admin,
            material=self.raw_material,
            status='IN_STOCK',
        )
        Inventory.objects.create(
            product=self.raw_material,
            warehouse=self.sklad1,
            quantity=100,
            reserved_quantity=0,
            batch_number='RAW-001',
        )
        Stock.objects.create(warehouse=self.sklad1, material=self.raw_material, quantity=100)
        document = Document.objects.create(
            type='ICHKI_YUK_XATI',
            number='INT-RAW-001',
            from_warehouse=self.sklad1,
            to_warehouse=self.sklad4,
            created_by=self.admin,
        )
        DocumentItem.objects.create(
            document=document,
            product=self.raw_material,
            quantity=20,
            price_at_moment=Decimal('0'),
            batch_number='RAW-001',
        )

        confirm_document(document, user=self.admin)
        self.assertEqual(BatchReservation.objects.filter(document=document).count(), 1)

        complete_document(document, user=self.admin)

        batch = RawMaterialBatch.objects.get(batch_number='RAW-001')
        stock = Stock.objects.get(warehouse=self.sklad1, material=self.raw_material)
        inventory = Inventory.objects.get(product=self.raw_material, warehouse=self.sklad1, batch_number='RAW-001')
        self.assertEqual(batch.remaining_quantity, 80)
        self.assertEqual(batch.reserved_quantity, 0)
        self.assertEqual(stock.quantity, 80)
        self.assertEqual(inventory.quantity, 80)
