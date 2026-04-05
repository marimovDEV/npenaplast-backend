from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from documents.models import Document
from warehouse_v2.models import Material

from .models import ProductionOrder, ProductionPlan, ProductionOrderStage, Recipe, RecipeItem, Zames, BlockProduction, DryingProcess
from .services import create_production_order, force_complete_stage, start_production_stage


class ProductionSafetyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='production-admin',
            password='testpass123',
            full_name='Production Admin',
            phone='+998900000010',
            role='Bosh Admin',
        )
        self.sales_user = User.objects.create_user(
            username='production-sales',
            password='testpass123',
            full_name='Sales User',
            phone='+998900000011',
            role='Sotuv menejeri',
        )
        self.cnc_user = User.objects.create_user(
            username='production-cnc',
            password='testpass123',
            full_name='CNC User',
            phone='+998900000012',
            role='CNC operatori',
        )
        self.client.force_authenticate(self.user)
        self.product = Material.objects.create(name='EPS Block', unit='dona', category='FINISHED')
        self.raw_material = Material.objects.create(name='Granula', unit='kg', category='RAW')

    def test_material_needs_endpoint_uses_service_without_runtime_error(self):
        order = ProductionOrder.objects.create(order_number='PO-001', product=self.product, quantity=5)
        plan = ProductionPlan.objects.create(date='2026-04-01')
        plan.orders.add(order)
        recipe = Recipe.objects.create(product=self.product, name='Recipe 1')
        RecipeItem.objects.create(recipe=recipe, material=self.raw_material, quantity=2)

        response = self.client.get(f'/api/production/plans/{plan.id}/material_needs/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {str(self.raw_material.id): 10})

    def test_force_complete_stage_advances_pipeline(self):
        order = ProductionOrder.objects.create(order_number='PO-002', product=self.product, quantity=1)
        first_stage = ProductionOrderStage.objects.create(order=order, stage_type='ZAMES', sequence=0, status='ACTIVE')
        second_stage = ProductionOrderStage.objects.create(order=order, stage_type='DRYING', sequence=1, status='PENDING')

        force_complete_stage(first_stage.id, user=self.user, reason='Emergency override')

        first_stage.refresh_from_db()
        second_stage.refresh_from_db()
        self.assertEqual(first_stage.status, 'DONE')
        self.assertEqual(second_stage.status, 'PENDING')

    def test_create_production_order_creates_backing_document(self):
        order = create_production_order(
            product=self.product,
            quantity=7,
            order_number='PO-003',
            user=self.user,
        )

        document = Document.objects.get(type='PRODUCTION_ORDER', number='PO-003')
        self.assertEqual(document.items.count(), 1)
        self.assertEqual(document.items.first().quantity, 7)
        self.assertEqual(order.order_number, document.number)

    def test_start_stage_creates_stage_update_document(self):
        order = ProductionOrder.objects.create(order_number='PO-004', product=self.product, quantity=2)
        stage = ProductionOrderStage.objects.create(order=order, stage_type='ZAMES', sequence=0, status='PENDING')

        start_production_stage(stage.id, user=self.user)

        stage.refresh_from_db()
        self.assertEqual(stage.status, 'ACTIVE')
        self.assertTrue(Document.objects.filter(type='STAGE_UPDATE', number='PO-004-ZAMES-01-START').exists())

    def test_order_actions_reject_foreign_stage_ids(self):
        first_order = ProductionOrder.objects.create(order_number='PO-005', product=self.product, quantity=1)
        second_order = ProductionOrder.objects.create(order_number='PO-006', product=self.product, quantity=1)
        foreign_stage = ProductionOrderStage.objects.create(order=second_order, stage_type='ZAMES', sequence=0, status='PENDING')

        response = self.client.post(
            f'/api/production/orders/{first_order.id}/start-stage/',
            {'stage_id': foreign_stage.id},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('tegishli emas', response.json()['error'])

    def test_production_order_endpoint_forbids_unrelated_role(self):
        self.client.force_authenticate(self.sales_user)
        response = self.client.get('/api/production/orders/')
        self.assertEqual(response.status_code, 403)

    def test_supervisor_actions_forbid_non_supervisor_production_roles(self):
        order = ProductionOrder.objects.create(order_number='PO-007', product=self.product, quantity=1)
        stage = ProductionOrderStage.objects.create(order=order, stage_type='ZAMES', sequence=0, status='PENDING')

        self.client.force_authenticate(self.cnc_user)
        assign_response = self.client.post(
            f'/api/production/orders/{order.id}/assign-task/',
            {'stage_id': stage.id, 'operator_id': self.cnc_user.id},
            format='json',
        )
        force_response = self.client.post(
            f'/api/production/orders/{order.id}/force-complete/',
            {'stage_id': stage.id},
            format='json',
        )
        reset_response = self.client.post(
            f'/api/production/orders/{order.id}/reset-stage/',
            {'stage_id': stage.id},
            format='json',
        )

        self.assertEqual(assign_response.status_code, 403)
        self.assertEqual(force_response.status_code, 403)
        self.assertEqual(reset_response.status_code, 403)

    def test_usta_can_use_supervisor_actions(self):
        usta = User.objects.create_user(
            username='production-usta',
            password='testpass123',
            full_name='Production Usta',
            phone='+998900000013',
            role='Ishlab chiqarish ustasi',
        )
        order = ProductionOrder.objects.create(order_number='PO-008', product=self.product, quantity=1)
        stage = ProductionOrderStage.objects.create(order=order, stage_type='ZAMES', sequence=0, status='PENDING')

        self.client.force_authenticate(usta)
        response = self.client.post(
            f'/api/production/orders/{order.id}/assign-task/',
            {'stage_id': stage.id, 'operator_id': usta.id},
            format='json',
        )

        self.assertEqual(response.status_code, 200)

    def test_production_task_compatibility_is_role_scoped_and_patchable(self):
        usta = User.objects.create_user(
            username='production-compat-usta',
            password='testpass123',
            full_name='Compat Usta',
            phone='+998900000014',
            role='Ishlab chiqarish ustasi',
        )
        zames = Zames.objects.create(zames_number='Z-COMP-001', status='DONE', operator=usta)
        block = BlockProduction.objects.create(
            zames=zames,
            form_number='FORM-COMP-001',
            block_count=1,
            status='DRYING',
        )
        drying = DryingProcess.objects.create(block_production=block)

        self.client.force_authenticate(usta)
        list_response = self.client.get('/api/production-tasks/')
        patch_response = self.client.patch(
            f'/api/production-tasks/{drying.id}/',
            {'is_completed': True},
            format='json',
        )

        drying.refresh_from_db()
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data[0]['responsible_person_name'], 'Compat Usta')
        self.assertEqual(patch_response.status_code, 200)
        self.assertIsNotNone(drying.end_time)

        self.client.force_authenticate(self.sales_user)
        forbidden_response = self.client.get('/api/production-tasks/')
        self.assertEqual(forbidden_response.status_code, 403)
