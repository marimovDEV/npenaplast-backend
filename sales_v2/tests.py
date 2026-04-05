from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from finance_v2.models import Cashbox, FinancialTransaction
from inventory.models import Inventory
from production_v2.models import ProductionOrder
from production_v2.services import force_complete_stage
from warehouse_v2.models import Material, Warehouse

from .models import Customer, Delivery, Invoice
from .services import create_invoice, transition_invoice_status


class SalesSafetyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='sales-admin',
            password='testpass123',
            full_name='Sales Admin',
            phone='+998900000201',
            role='Bosh Admin',
        )
        self.sales_manager = User.objects.create_user(
            username='sales-manager',
            password='testpass123',
            full_name='Sales Manager',
            phone='+998900000203',
            role='Sotuv menejeri',
        )
        self.courier = User.objects.create_user(
            username='courier-user',
            password='testpass123',
            full_name='Courier User',
            phone='+998900000204',
            role='Kuryer',
        )
        self.operator = User.objects.create_user(
            username='warehouse-operator',
            password='testpass123',
            full_name='Warehouse Operator',
            phone='+998900000205',
            role='Omborchi',
        )
        self.customer = Customer.objects.create(name='Customer 1', phone='+998900000202')
        self.warehouse = Warehouse.objects.create(name='Sklad №4')
        self.product = Material.objects.create(name='Decor Panel', unit='dona', category='FINISHED')
        self.inventory = Inventory.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            quantity=10,
            reserved_quantity=0,
            batch_number='BATCH-001',
        )

    def test_create_invoice_reserves_requested_batch(self):
        invoice = create_invoice(
            warehouse_id=self.warehouse.id,
            customer_id=self.customer.id,
            items=[{
                'product_id': self.product.id,
                'quantity': 3,
                'price': 100,
                'batch_number': 'BATCH-001',
            }],
            created_by=self.user,
        )

        self.inventory.refresh_from_db()
        self.assertEqual(invoice.total_amount, 300)
        self.assertEqual(self.inventory.reserved_quantity, 3)
        sale_item = invoice.items.get()
        self.assertEqual(sale_item.batch_number, 'BATCH-001')
        self.assertEqual(sale_item.source_warehouse_id, self.warehouse.id)

    def test_create_invoice_rejects_discount_greater_than_total(self):
        with self.assertRaisesMessage(Exception, "Chegirma umumiy summadan katta bo'lishi mumkin emas."):
            create_invoice(
                warehouse_id=self.warehouse.id,
                customer_id=self.customer.id,
                items=[{
                    'product_id': self.product.id,
                    'quantity': 1,
                    'price': 100,
                    'batch_number': 'BATCH-001',
                }],
                discount_amount=150,
                created_by=self.user,
            )

    def test_completing_cash_invoice_requires_active_cashbox(self):
        invoice = create_invoice(
            warehouse_id=self.warehouse.id,
            customer_id=self.customer.id,
            items=[{
                'product_id': self.product.id,
                'quantity': 1,
                'price': 100,
                'batch_number': 'BATCH-001',
            }],
            payment_method='CASH',
            created_by=self.user,
        )

        transition_invoice_status(invoice.id, 'CONFIRMED', performed_by=self.user)

        with self.assertRaisesMessage(Exception, "Mos aktiv kassa topilmadi."):
            transition_invoice_status(invoice.id, 'COMPLETED', performed_by=self.user)

        Cashbox.objects.create(name='Main Cash', type='CASH', balance=Decimal('0.00'), is_active=True)
        transition_invoice_status(invoice.id, 'COMPLETED', performed_by=self.user)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'COMPLETED')

    def test_cancelling_invoice_releases_same_reserved_batch(self):
        other_inventory = Inventory.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            quantity=8,
            reserved_quantity=4,
            batch_number='BATCH-XYZ',
        )
        invoice = create_invoice(
            warehouse_id=self.warehouse.id,
            customer_id=self.customer.id,
            items=[{
                'product_id': self.product.id,
                'quantity': 2,
                'price': 100,
                'batch_number': 'BATCH-001',
            }],
            created_by=self.user,
        )

        transition_invoice_status(invoice.id, 'CANCELLED', performed_by=self.user)

        self.inventory.refresh_from_db()
        other_inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, 0)
        self.assertEqual(other_inventory.reserved_quantity, 4)

    def test_shipping_uses_sale_item_batch_and_releases_only_that_reservation(self):
        invoice = create_invoice(
            warehouse_id=self.warehouse.id,
            customer_id=self.customer.id,
            items=[{
                'product_id': self.product.id,
                'quantity': 2,
                'price': 100,
                'batch_number': 'BATCH-001',
            }],
            created_by=self.user,
        )

        transition_invoice_status(invoice.id, 'SHIPPED', performed_by=self.user)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 8)
        self.assertEqual(self.inventory.reserved_quantity, 0)

    def test_invoice_delete_is_blocked(self):
        invoice = create_invoice(
            warehouse_id=self.warehouse.id,
            customer_id=self.customer.id,
            items=[{
                'product_id': self.product.id,
                'quantity': 1,
                'price': 100,
                'batch_number': 'BATCH-001',
            }],
            created_by=self.user,
        )
        self.client.force_authenticate(self.user)
        response = self.client.delete(f'/api/sales/invoices/{invoice.id}/')
        self.assertEqual(response.status_code, 405)

    def test_sales_endpoints_are_forbidden_for_unrelated_role(self):
        self.client.force_authenticate(self.operator)
        response = self.client.get('/api/sales/customers/')
        self.assertEqual(response.status_code, 403)

    def test_sales_export_endpoint_returns_file(self):
        create_invoice(
            warehouse_id=self.warehouse.id,
            customer_id=self.customer.id,
            items=[{
                'product_id': self.product.id,
                'quantity': 1,
                'price': 100,
                'batch_number': 'BATCH-001',
            }],
            created_by=self.user,
        )
        self.client.force_authenticate(self.sales_manager)
        response = self.client.get('/api/sales/export/?file_format=PDF&period=This%20Month')
        self.assertEqual(response.status_code, 200)

    def test_courier_only_sees_own_deliveries(self):
        own_invoice = Invoice.objects.create(
            invoice_number='INV-OWN',
            customer=self.customer,
            total_amount=100,
            status='SHIPPED',
            created_by=self.user,
        )
        other_invoice = Invoice.objects.create(
            invoice_number='INV-OTHER',
            customer=self.customer,
            total_amount=120,
            status='SHIPPED',
            created_by=self.user,
        )
        own_delivery = Delivery.objects.create(invoice=own_invoice, courier=self.courier, status='PENDING')
        other_courier = User.objects.create_user(
            username='courier-other',
            password='testpass123',
            full_name='Courier Other',
            phone='+998900000206',
            role='Kuryer',
        )
        other_delivery = Delivery.objects.create(invoice=other_invoice, courier=other_courier, status='PENDING')

        self.client.force_authenticate(self.courier)
        list_response = self.client.get('/api/sales/deliveries/')
        pickup_response = self.client.post(f'/api/sales/deliveries/{other_delivery.id}/pickup/')
        my_response = self.client.get('/api/sales/deliveries/my-deliveries/')

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]['id'], own_delivery.id)
        self.assertEqual(pickup_response.status_code, 404)
        self.assertEqual(my_response.status_code, 200)
        self.assertEqual(len(my_response.data), 1)
        self.assertEqual(my_response.data[0]['id'], own_delivery.id)

    def test_end_to_end_sale_production_shipping_and_finance_flow(self):
        made_to_order_invoice = create_invoice(
            warehouse_id=self.warehouse.id,
            customer_id=self.customer.id,
            items=[{
                'product_id': self.product.id,
                'quantity': 4,
                'price': 125,
            }],
            payment_method='CASH',
            created_by=self.user,
        )

        transition_invoice_status(made_to_order_invoice.id, 'CONFIRMED', performed_by=self.user)
        made_to_order_invoice.refresh_from_db()
        self.assertEqual(made_to_order_invoice.status, 'IN_PRODUCTION')

        production_order = ProductionOrder.objects.get(source_order=made_to_order_invoice.invoice_number)
        self.assertEqual(production_order.product, self.product)

        for stage in production_order.stages.order_by('sequence'):
            force_complete_stage(stage.id, user=self.user, reason='E2E flow test')

        made_to_order_invoice.refresh_from_db()
        sale_item = made_to_order_invoice.items.get()
        self.assertEqual(made_to_order_invoice.status, 'READY')
        self.assertEqual(sale_item.batch_number, f'PROD-{production_order.order_number}')
        self.assertEqual(sale_item.source_warehouse_id, self.warehouse.id)

        produced_inventory = Inventory.objects.get(
            product=self.product,
            warehouse=self.warehouse,
            batch_number=f'PROD-{production_order.order_number}',
        )
        self.assertEqual(produced_inventory.quantity, 4)

        transition_invoice_status(made_to_order_invoice.id, 'SHIPPED', performed_by=self.user)
        produced_inventory.refresh_from_db()
        made_to_order_invoice.refresh_from_db()
        self.assertEqual(made_to_order_invoice.status, 'SHIPPED')
        self.assertEqual(produced_inventory.quantity, 0)
        self.assertTrue(hasattr(made_to_order_invoice, 'delivery'))

        Cashbox.objects.create(name='Main Cash E2E', type='CASH', balance=Decimal('0.00'), is_active=True)
        transition_invoice_status(made_to_order_invoice.id, 'COMPLETED', performed_by=self.user)

        made_to_order_invoice.refresh_from_db()
        self.assertEqual(made_to_order_invoice.status, 'COMPLETED')
        self.assertTrue(
            FinancialTransaction.objects.filter(
                customer=self.customer,
                type='INCOME',
                description__icontains=made_to_order_invoice.invoice_number,
            ).exists()
        )
