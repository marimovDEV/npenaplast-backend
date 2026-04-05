from django.db import models
from django.conf import settings

class ConstructionProject(models.Model):
    STATUS_CHOICES = (
        ('PLANNED', 'Rejalashtirilgan'),
        ('IN_PROGRESS', 'Jarayonda'),
        ('PAUSED', 'To\'xtatilgan'),
        ('COMPLETED', 'Tugallangan'),
        ('CANCELLED', 'Bekor qilingan'),
    )
    
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='managed_projects')
    start_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED')
    description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Soft deletion
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

class ProjectSupply(models.Model):
    project = models.ForeignKey(ConstructionProject, on_delete=models.CASCADE, related_name='supplies')
    product = models.ForeignKey('warehouse_v2.Material', on_delete=models.CASCADE)
    batch = models.ForeignKey('inventory.InventoryBatch', on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.DecimalField(max_digits=15, decimal_places=3)
    date = models.DateField(auto_now_add=True)
    from_warehouse = models.ForeignKey('warehouse_v2.Warehouse', on_delete=models.PROTECT)
    
    # Connection to accounting and inventory movement
    transaction = models.OneToOneField('finance.Transaction', on_delete=models.SET_NULL, null=True, blank=True)
    movement = models.OneToOneField('inventory.InventoryMovement', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Supply to {self.project.name}: {self.quantity} {self.product.unit} of {self.product.name}"
