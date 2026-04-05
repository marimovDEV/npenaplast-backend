from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from sales_v2.models import Customer

from .models import Cashbox, FinancialTransaction, InternalTransfer


class FinanceSafetyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='finance-admin',
            password='testpass123',
            full_name='Finance Admin',
            phone='+998900000001',
            role='Bosh Admin',
        )
        self.sales_user = User.objects.create_user(
            username='sales-user',
            password='testpass123',
            full_name='Sales User',
            phone='+998900000003',
            role='Sotuv menejeri',
        )
        self.operator_user = User.objects.create_user(
            username='warehouse-user',
            password='testpass123',
            full_name='Warehouse User',
            phone='+998900000004',
            role='Omborchi',
        )
        self.cashbox = Cashbox.objects.create(name='Main Cashbox', balance=Decimal('1000.00'))
        self.secondary_cashbox = Cashbox.objects.create(name='Secondary Cashbox', balance=Decimal('200.00'))
        self.customer = Customer.objects.create(name='Test Customer', phone='+998900000002')

    def test_expense_cannot_overdraw_cashbox(self):
        tx = FinancialTransaction(
            cashbox=self.cashbox,
            amount=Decimal('1500.00'),
            type='EXPENSE',
            customer=self.customer,
            performed_by=self.user,
        )

        with self.assertRaises(ValidationError):
            tx.save()

        self.cashbox.refresh_from_db()
        self.assertEqual(self.cashbox.balance, Decimal('1000.00'))

    def test_internal_transfer_requires_distinct_cashboxes(self):
        transfer = InternalTransfer(
            from_cashbox=self.cashbox,
            to_cashbox=self.cashbox,
            amount=Decimal('100.00'),
            performed_by=self.user,
        )

        with self.assertRaises(ValidationError):
            transfer.save()

    def test_internal_transfer_updates_both_balances_atomically(self):
        InternalTransfer.objects.create(
            from_cashbox=self.cashbox,
            to_cashbox=self.secondary_cashbox,
            amount=Decimal('150.00'),
            performed_by=self.user,
        )

        self.cashbox.refresh_from_db()
        self.secondary_cashbox.refresh_from_db()
        self.assertEqual(self.cashbox.balance, Decimal('850.00'))
        self.assertEqual(self.secondary_cashbox.balance, Decimal('350.00'))

    def test_cashbox_delete_is_blocked(self):
        self.client.force_authenticate(self.user)
        response = self.client.delete(f'/api/finance/cashboxes/{self.cashbox.id}/')
        self.assertEqual(response.status_code, 405)

    def test_cashbox_access_is_forbidden_for_unrelated_role(self):
        self.client.force_authenticate(self.operator_user)
        response = self.client.get('/api/finance/cashboxes/')
        self.assertEqual(response.status_code, 403)

    def test_finance_export_endpoint_returns_file(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/finance/export/?file_format=EXCEL&period=This%20Month')
        self.assertEqual(response.status_code, 200)

    def test_sales_manager_can_access_finance_views_and_create_transaction(self):
        self.client.force_authenticate(self.sales_user)
        cashbox_response = self.client.get('/api/finance/cashboxes/')
        analytics_response = self.client.get('/api/finance/analytics/')
        create_response = self.client.post('/api/finance/transactions/', {
            'cashbox': self.cashbox.id,
            'amount': '50.00',
            'type': 'INCOME',
            'customer': self.customer.id,
            'description': 'Sales payment',
        }, format='json')

        self.assertEqual(cashbox_response.status_code, 200)
        self.assertEqual(analytics_response.status_code, 200)
        self.assertEqual(create_response.status_code, 201)

    def test_sales_manager_cannot_create_internal_transfer(self):
        self.client.force_authenticate(self.sales_user)
        response = self.client.post('/api/finance/transfers/', {
            'from_cashbox': self.cashbox.id,
            'to_cashbox': self.secondary_cashbox.id,
            'amount': '25.00',
        }, format='json')
        self.assertEqual(response.status_code, 403)

    def test_operator_cannot_create_financial_transaction(self):
        self.client.force_authenticate(self.operator_user)
        response = self.client.post('/api/finance/transactions/', {
            'cashbox': self.cashbox.id,
            'amount': '10.00',
            'type': 'INCOME',
            'customer': self.customer.id,
        }, format='json')
        self.assertEqual(response.status_code, 403)
