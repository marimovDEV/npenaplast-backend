from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User

from .models import WasteCategory
from .services import accept_waste, finish_processing_waste, start_processing_waste


class WasteSafetyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='waste-admin',
            password='testpass123',
            full_name='Waste Admin',
            phone='+998900002201',
            role='Bosh Admin',
        )
        self.category = WasteCategory.objects.create(name='Foam Waste', norm_percent=5)
        self.waste_operator = User.objects.create_user(
            username='waste-operator',
            password='testpass123',
            full_name='Waste Operator',
            phone='+998900002202',
            role='Chiqindi operatori',
        )
        self.sales = User.objects.create_user(
            username='waste-sales',
            password='testpass123',
            full_name='Waste Sales',
            phone='+998900002203',
            role='Sotuv menejeri',
        )

    def test_accept_waste_rejects_non_positive_weight(self):
        with self.assertRaises(ValueError):
            accept_waste('CNC', 0, self.category.id, operator=self.user)

    def test_finish_processing_rejects_invalid_weight_breakdown(self):
        task = accept_waste('CNC', 10, self.category.id, operator=self.user)
        start_processing_waste(task.id)

        with self.assertRaises(ValueError):
            finish_processing_waste(task.id, recycled_weight_kg=8, loss_weight_kg=3)

    def test_waste_operator_can_run_task_flow_via_api(self):
        self.client.force_authenticate(self.waste_operator)
        create_response = self.client.post('/api/waste/tasks/', {
            'source_department': 'CNC',
            'weight_kg': 12,
            'category': self.category.id,
            'batch_number': 'WASTE-001',
        })
        self.assertEqual(create_response.status_code, 201)

        task_id = create_response.data['id']
        start_response = self.client.post(f'/api/waste/tasks/{task_id}/start/')
        finish_response = self.client.post(f'/api/waste/tasks/{task_id}/finish/', {
            'recycled_weight_kg': 8,
            'loss_weight_kg': 4,
            'notes': 'Processed',
        })

        self.assertEqual(start_response.status_code, 200)
        self.assertEqual(finish_response.status_code, 200)

    def test_sales_cannot_create_waste_task(self):
        self.client.force_authenticate(self.sales)
        response = self.client.post('/api/waste/tasks/', {
            'source_department': 'CNC',
            'weight_kg': 5,
            'category': self.category.id,
            'batch_number': 'WASTE-002',
        })
        self.assertEqual(response.status_code, 403)
