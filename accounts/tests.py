from django.test import TestCase

from warehouse_v2.models import Warehouse

from .models import ERPRole, User
from .permissions import IsAdmin, IsWarehouseOperator
from .serializers import UserSerializer


class _DummyRequest:
    def __init__(self, user):
        self.user = user


class UserSerializerSafetyTests(TestCase):
    def setUp(self):
        self.warehouse1 = Warehouse.objects.create(name='Sklad 1')
        self.warehouse2 = Warehouse.objects.create(name='Sklad 2')
        self.admin_role = ERPRole.objects.create(name='Admin')
        self.warehouse_role = ERPRole.objects.create(name='Omborchi')

    def test_create_user_with_assigned_warehouses(self):
        serializer = UserSerializer(data={
            'username': 'user-one',
            'full_name': 'User One',
            'phone': '+998900000101',
            'password': 'testpass123',
            'assigned_warehouses': [self.warehouse1.id, self.warehouse2.id],
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertEqual(user.assigned_warehouses.count(), 2)
        self.assertTrue(user.check_password('testpass123'))

    def test_create_user_syncs_legacy_role_from_role_obj(self):
        serializer = UserSerializer(data={
            'username': 'warehouse-one',
            'full_name': 'Warehouse One',
            'phone': '+998900000103',
            'password': 'testpass123',
            'role_id': self.warehouse_role.id,
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertEqual(user.role, 'Omborchi')
        self.assertEqual(serializer.data['effective_role'], 'Omborchi')
        self.assertIn('warehouse.receive', serializer.data['task_scope'])

    def test_update_user_assigned_warehouses(self):
        create_serializer = UserSerializer(data={
            'username': 'user-two',
            'full_name': 'User Two',
            'phone': '+998900000102',
            'password': 'testpass123',
            'assigned_warehouses': [self.warehouse1.id],
        })
        self.assertTrue(create_serializer.is_valid(), create_serializer.errors)
        user = create_serializer.save()

        update_serializer = UserSerializer(
            instance=user,
            data={'assigned_warehouses': [self.warehouse2.id]},
            partial=True,
        )
        self.assertTrue(update_serializer.is_valid(), update_serializer.errors)
        user = update_serializer.save()

        self.assertEqual(list(user.assigned_warehouses.values_list('id', flat=True)), [self.warehouse2.id])

    def test_update_user_syncs_role_when_role_obj_changes(self):
        user = User.objects.create(username='role-sync', full_name='Role Sync', phone='+998900000104', role='Admin')
        serializer = UserSerializer(instance=user, data={'role_id': self.warehouse_role.id}, partial=True)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_user = serializer.save()

        self.assertEqual(updated_user.role, 'Omborchi')


class RolePermissionTests(TestCase):
    def test_admin_role_obj_is_treated_as_admin(self):
        role = ERPRole.objects.create(name='Admin')
        user = User.objects.create(username='admin-role', full_name='Admin Role', phone='+998900000105', role_obj=role)

        self.assertTrue(IsAdmin().has_permission(_DummyRequest(user), None))
        self.assertTrue(IsWarehouseOperator().has_permission(_DummyRequest(user), None))
