from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from datetime import timedelta

from accounts.models import User
from cnc_v2.models import WasteProcessing
from warehouse_v2.models import Material, Stock, Warehouse
from sales_v2.models import Customer, Invoice


class ReportExportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='report-admin',
            password='testpass123',
            full_name='Report Admin',
            phone='+998900000301',
            role='Bosh Admin',
        )
        customer = Customer.objects.create(name='Report Customer', phone='+998900000302')
        Invoice.objects.create(
            invoice_number='ORD-9001',
            customer=customer,
            total_amount=150000,
            status='COMPLETED',
            payment_method='CASH',
            created_by=self.user,
        )
        self.client.force_authenticate(self.user)

    def test_sales_report_excludes_cancelled_invoices(self):
        customer = Customer.objects.create(name='Cancelled Customer', phone='+998900000303')
        Invoice.objects.create(
            invoice_number='ORD-9002',
            customer=customer,
            total_amount=50000,
            status='CANCELLED',
            payment_method='CASH',
            created_by=self.user,
        )

        response = self.client.get('/api/reports/sales/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['invoice_count'], 1)
        self.assertEqual(float(response.data['total_revenue']), 150000.0)

    def test_general_analytics_uses_only_valid_sales_and_real_waste_metric(self):
        customer = Customer.objects.create(name='Analytics Customer', phone='+998900000304')
        Invoice.objects.create(
            invoice_number='ORD-9003',
            customer=customer,
            total_amount=90000,
            status='CANCELLED',
            payment_method='CASH',
            created_by=self.user,
        )
        WasteProcessing.objects.create(
            source_department='CNC',
            reason='CUTTING',
            waste_amount_kg=25,
            operator=self.user,
        )

        response = self.client.get('/api/reports/analytics/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['kpis']['total_sales'], 150000.0)
        self.assertEqual(response.data['kpis']['total_waste_kg'], 25.0)

    def test_dashboard_summary_uses_real_warehouse_names_and_overdue_logic(self):
        raw = Material.objects.create(name='Raw Test', unit='kg', category='RAW')
        Warehouse.objects.create(name='Sklad №1')
        Warehouse.objects.create(name='Sklad №2')
        Warehouse.objects.create(name='Sklad №3')
        Warehouse.objects.create(name='Sklad №4')
        Stock.objects.create(warehouse=Warehouse.objects.get(name='Sklad №1'), material=raw, quantity=11)
        Stock.objects.create(warehouse=Warehouse.objects.get(name='Sklad №2'), material=raw, quantity=22)
        Stock.objects.create(warehouse=Warehouse.objects.get(name='Sklad №3'), material=raw, quantity=33)
        Stock.objects.create(warehouse=Warehouse.objects.get(name='Sklad №4'), material=raw, quantity=44)

        response = self.client.get('/api/dashboard/summary/?period=week')

        self.assertEqual(response.status_code, 200)
        stats = response.data['stats']
        self.assertIn('11', stats[0]['value'])
        self.assertIn('22', stats[1]['value'])
        self.assertIn('33', stats[2]['value'])
        self.assertIn('44', stats[3]['value'])

    def test_dashboard_summary_scopes_warehouse_stats_for_assigned_operator(self):
        raw = Material.objects.create(name='Scoped Raw', unit='kg', category='RAW')
        sklad1 = Warehouse.objects.create(name='Sklad №1')
        sklad2 = Warehouse.objects.create(name='Sklad №2')
        Stock.objects.create(warehouse=sklad1, material=raw, quantity=15)
        Stock.objects.create(warehouse=sklad2, material=raw, quantity=99)
        operator = User.objects.create_user(
            username='report-omborchi',
            password='testpass123',
            full_name='Scoped Omborchi',
            phone='+998900000305',
            role='Omborchi',
        )
        operator.assigned_warehouses.add(sklad1)

        self.client.force_authenticate(operator)
        response = self.client.get('/api/dashboard/summary/?period=week')

        self.assertEqual(response.status_code, 200)
        stats = response.data['stats']
        self.assertIn('15', stats[0]['value'])
        self.assertIn('0', stats[1]['value'])

    def test_dashboard_summary_hides_warehouse_stats_without_assignment(self):
        raw = Material.objects.create(name='No Scope Raw', unit='kg', category='RAW')
        sklad1 = Warehouse.objects.create(name='Sklad №1')
        Stock.objects.create(warehouse=sklad1, material=raw, quantity=77)
        operator = User.objects.create_user(
            username='report-unassigned',
            password='testpass123',
            full_name='Unassigned Omborchi',
            phone='+998900000306',
            role='Omborchi',
        )

        self.client.force_authenticate(operator)
        response = self.client.get('/api/dashboard/summary/?period=week')

        self.assertEqual(response.status_code, 200)
        self.assertIn('0', response.data['stats'][0]['value'])
        self.assertEqual(response.data['recentKirim'], [])

    def test_dashboard_summary_scopes_sales_metrics_for_sales_manager(self):
        sales_user = User.objects.create_user(
            username='sales-manager-dashboard',
            password='testpass123',
            full_name='Scoped Sales',
            phone='+998900000307',
            role='Sotuv menejeri',
        )
        other_user = User.objects.create_user(
            username='other-sales-dashboard',
            password='testpass123',
            full_name='Other Sales',
            phone='+998900000308',
            role='Sotuv menejeri',
        )
        own_customer = Customer.objects.create(
            name='Own Customer',
            phone='+998900000309',
            assigned_manager=sales_user,
        )
        other_customer = Customer.objects.create(
            name='Other Customer',
            phone='+998900000310',
            assigned_manager=other_user,
        )
        own_invoice = Invoice.objects.create(
            invoice_number='ORD-9101',
            customer=own_customer,
            total_amount=120000,
            status='COMPLETED',
            payment_method='CASH',
            created_by=sales_user,
        )
        other_invoice = Invoice.objects.create(
            invoice_number='ORD-9102',
            customer=other_customer,
            total_amount=220000,
            status='COMPLETED',
            payment_method='CASH',
            created_by=other_user,
        )
        overdue_own = Invoice.objects.create(
            invoice_number='ORD-9103',
            customer=own_customer,
            total_amount=100000,
            status='READY',
            payment_method='CASH',
            created_by=sales_user,
        )
        overdue_other = Invoice.objects.create(
            invoice_number='ORD-9104',
            customer=other_customer,
            total_amount=110000,
            status='READY',
            payment_method='CASH',
            created_by=other_user,
        )
        old_date = timezone.now() - timedelta(days=5)
        Invoice.objects.filter(id__in=[overdue_own.id, overdue_other.id]).update(date=old_date)

        self.client.force_authenticate(sales_user)
        response = self.client.get('/api/dashboard/summary/?period=week')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['todayStats']['sales_count'], 2)
        self.assertEqual(len(response.data['recentSales']), 2)
        self.assertEqual(response.data['overdueCount'], 1)
        invoice_numbers = {item['invoice_number'] for item in response.data['recentSales']}
        self.assertIn(own_invoice.invoice_number, invoice_numbers)
        self.assertIn(overdue_own.invoice_number, invoice_numbers)
        self.assertNotIn(other_invoice.invoice_number, invoice_numbers)

    def test_generate_excel_report_creates_file(self):
        response = self.client.post('/api/reports/history/', {
            'name': 'Sales Export',
            'report_type': 'SALES',
            'period': 'This Month',
            'file_format': 'EXCEL',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['file_path'])
        self.assertEqual(response.data['status'], 'READY')

    def test_download_generated_pdf_report(self):
        create_response = self.client.post('/api/reports/history/', {
            'name': 'Sales PDF Export',
            'report_type': 'SALES',
            'period': 'This Month',
            'file_format': 'PDF',
        }, format='json')
        report_id = create_response.data['id']

        download_response = self.client.get(f'/api/reports/history/{report_id}/download/')

        self.assertEqual(download_response.status_code, 200)
