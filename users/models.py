from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('SuperAdmin', 'Super Admin'),
        ('Admin', 'Admin'),
        ('WarehouseOperator', 'Warehouse Operator'),
        ('ProductionOperator', 'Production Operator'),
        ('CNCOperator', 'CNC Operator'),
        ('FinishingOperator', 'Finishing Operator'),
        ('WasteOperator', 'Waste Operator'),
        ('Salesperson', 'Salesperson'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    assigned_warehouses = models.ManyToManyField('warehouse.Warehouse', blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"
