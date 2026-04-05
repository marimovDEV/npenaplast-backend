from django.db import models
from django.conf import settings

class Product(models.Model):
    TYPE_CHOICES = (
        ('RAW', 'Raw Material'),
        ('EXPANDED', 'Expanded Granule'),
        ('BLOCK', 'Solid Block'),
        ('FINISHED', 'Finished Product'),
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    unit = models.CharField(max_length=20)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name

class ProductionTask(models.Model):
    STAGE_CHOICES = (
        ('CNC', 'CNC Cutting'),
        ('FINISHING', 'Armirlash/Shpaklyovka'),
        ('DRYING', 'Drying'),
        ('READY', 'Ready for Sklad 4'),
    )
    name = models.CharField(max_length=100)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='CNC')
    priority = models.IntegerField(default=1) # 1: Low, 2: Medium, 3: High
    deadline = models.DateField(null=True, blank=True)
    responsible_person = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    quantity = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.stage}"
