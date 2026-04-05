from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from accounts.models import User
from inventory.models import Inventory
from production_v2.models import BlockProduction, Zames, ZamesItem
from warehouse_v2.models import Material, Warehouse

from .models import CNCJob
from .services import finish_cnc_job


class CNCSafetyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='cnc-admin',
            password='testpass123',
            full_name='CNC Admin',
            phone='+998900002001',
            role='Bosh Admin',
        )
        self.sklad2 = Warehouse.objects.create(name='Sklad №2')
        self.sklad3 = Warehouse.objects.create(name='Sklad №3')
        self.raw_material = Material.objects.create(name='Block Raw', unit='dona', category='SEMI')
        self.output_product = Material.objects.create(name='Decor CNC', unit='dona', category='SEMI')
        self.zames = Zames.objects.create(zames_number='Z-001', status='DONE', output_weight=100)
        ZamesItem.objects.create(zames=self.zames, material=self.raw_material, quantity=1)
        self.block = BlockProduction.objects.create(
            zames=self.zames,
            form_number='FORM-001',
            block_count=1,
            warehouse=self.sklad2,
            status='READY',
        )
        Inventory.objects.create(
            product=self.raw_material,
            warehouse=self.sklad2,
            quantity=1,
            reserved_quantity=0,
            batch_number='FORM-001',
        )
        self.job = CNCJob.objects.create(
            job_number='CNC-001',
            input_block=self.block,
            output_product=self.output_product,
            quantity_planned=5,
            machine_id='CNC-1',
            status='RUNNING',
            operator=self.user,
        )
        self.cnc_operator = User.objects.create_user(
            username='cnc-operator',
            password='testpass123',
            full_name='CNC Operator',
            phone='+998900002002',
            role='CNC operatori',
        )
        self.other_operator = User.objects.create_user(
            username='cnc-operator-2',
            password='testpass123',
            full_name='CNC Operator 2',
            phone='+998900002003',
            role='CNC operatori',
        )
        self.job.operator = self.cnc_operator
        self.job.save(update_fields=['operator'])

    def test_finish_cnc_job_rejects_output_above_plan(self):
        with self.assertRaises(ValidationError):
            finish_cnc_job(self.job.id, finished_qty=6, waste_m3=0, operator=self.user)

    def test_finish_cnc_job_adds_output_to_sklad3(self):
        finish_cnc_job(self.job.id, finished_qty=4, waste_m3=0.2, operator=self.user)

        output_inventory = Inventory.objects.get(
            product=self.output_product,
            warehouse=self.sklad3,
            batch_number='CNC-001',
        )
        input_inventory = Inventory.objects.get(
            product=self.raw_material,
            warehouse=self.sklad2,
            batch_number='FORM-001',
        )
        self.assertEqual(output_inventory.quantity, 4)
        self.assertEqual(input_inventory.quantity, 0)

    def test_cnc_operator_only_sees_own_jobs(self):
        foreign_job = CNCJob.objects.create(
            job_number='CNC-002',
            input_block=self.block,
            output_product=self.output_product,
            quantity_planned=2,
            machine_id='CNC-2',
            status='PENDING',
            operator=self.other_operator,
        )

        self.client.force_authenticate(self.cnc_operator)
        response = self.client.get('/api/cnc/jobs/')

        self.assertEqual(response.status_code, 200)
        returned_ids = {item['id'] for item in response.data}
        self.assertIn(self.job.id, returned_ids)
        self.assertNotIn(foreign_job.id, returned_ids)
