from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from accounts.models import User
from cnc_v2.models import CNCJob
from inventory.models import Inventory
from production_v2.models import BlockProduction, Zames, ZamesItem
from warehouse_v2.models import Material, Warehouse

from .models import FinishingJob
from .services import finish_finishing_job


class FinishingSafetyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='finishing-admin',
            password='testpass123',
            full_name='Finishing Admin',
            phone='+998900002101',
            role='Bosh Admin',
        )
        self.sklad3 = Warehouse.objects.create(name='Sklad №3')
        self.sklad4 = Warehouse.objects.create(name='Sklad №4')
        self.sklad2 = Warehouse.objects.create(name='Sklad №2')
        self.product = Material.objects.create(name='Decor Finish', unit='dona', category='SEMI')
        self.raw_material = Material.objects.create(name='Cut Block', unit='dona', category='SEMI')
        self.zames = Zames.objects.create(zames_number='Z-FIN-001', status='DONE', output_weight=100)
        ZamesItem.objects.create(zames=self.zames, material=self.raw_material, quantity=1)
        self.block = BlockProduction.objects.create(
            zames=self.zames,
            form_number='FORM-FIN-001',
            block_count=1,
            warehouse=self.sklad2,
            status='READY',
        )
        self.cnc_job = CNCJob.objects.create(
            job_number='CNC-FIN-001',
            input_block=self.block,
            output_product=self.product,
            quantity_planned=5,
            machine_id='CNC-1',
            status='COMPLETED',
            operator=self.user,
        )
        Inventory.objects.create(
            product=self.product,
            warehouse=self.sklad3,
            quantity=5,
            reserved_quantity=0,
            batch_number='CNC-FIN-001',
        )
        self.job = FinishingJob.objects.create(
            job_number='ARM-001',
            cnc_job=self.cnc_job,
            product=self.product,
            quantity=5,
            status='RUNNING',
            operator=self.user,
        )
        self.finishing_operator = User.objects.create_user(
            username='finishing-operator',
            password='testpass123',
            full_name='Finishing Operator',
            phone='+998900002102',
            role='Pardozlovchi',
        )
        self.other_operator = User.objects.create_user(
            username='finishing-operator-2',
            password='testpass123',
            full_name='Finishing Operator 2',
            phone='+998900002103',
            role='Pardozlovchi',
        )
        self.job.operator = self.finishing_operator
        self.job.save(update_fields=['operator'])

    def test_finish_finishing_job_rejects_quantities_above_plan(self):
        with self.assertRaises(ValidationError):
            finish_finishing_job(self.job.id, finished_qty=4, waste_qty=2, operator=self.user)

    def test_finish_finishing_job_moves_exact_batch_from_sklad3_to_sklad4(self):
        finish_finishing_job(self.job.id, finished_qty=4, waste_qty=1, operator=self.user)

        source_inventory = Inventory.objects.get(
            product=self.product,
            warehouse=self.sklad3,
            batch_number='CNC-FIN-001',
        )
        target_inventory = Inventory.objects.get(
            product=self.product,
            warehouse=self.sklad4,
            batch_number='ARM-001',
        )
        self.assertEqual(source_inventory.quantity, 0)
        self.assertEqual(target_inventory.quantity, 4)

    def test_finishing_operator_only_sees_own_jobs(self):
        foreign_job = FinishingJob.objects.create(
            job_number='ARM-002',
            cnc_job=self.cnc_job,
            product=self.product,
            quantity=2,
            status='PENDING',
            operator=self.other_operator,
        )

        self.client.force_authenticate(self.finishing_operator)
        response = self.client.get('/api/finishing/jobs/')

        self.assertEqual(response.status_code, 200)
        returned_ids = {item['id'] for item in response.data}
        self.assertIn(self.job.id, returned_ids)
        self.assertNotIn(foreign_job.id, returned_ids)
