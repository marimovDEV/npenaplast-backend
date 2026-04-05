import uuid
from django.db import models
from django.conf import settings

class ProductSource(models.TextChoices):
    INTERNAL = 'INTERNAL', 'O\'z mahsulotimiz (Produksiya)'
    EXTERNAL = 'EXTERNAL', 'Tashqaridan kelgan mahsulot'

class InventoryBatch(models.Model):
    STATUS_CHOICES = (
        ('IN_STOCK', 'Omborda'),
        ('RESERVED', 'Band qilingan'),
        ('DEPLETED', 'Tugatilgan'),
        ('PROJECT_USE', 'Loyiha uchun sarflangan'),
        ('WASTE', 'Chiqindi'),
    )
    
    batch_number = models.CharField(max_length=100, unique=True)
    product = models.ForeignKey('warehouse_v2.Material', on_delete=models.CASCADE, related_name='inventory_batches')
    source = models.CharField(max_length=20, choices=ProductSource.choices, default=ProductSource.EXTERNAL)
    
    initial_weight = models.DecimalField(max_digits=15, decimal_places=3, help_text="Starting weight in grams/kg")
    current_weight = models.DecimalField(max_digits=15, decimal_places=3, help_text="Current available weight")
    reserved_weight = models.DecimalField(max_digits=15, decimal_places=3, default=0, help_text="Reserved weight for orders")
    
    location = models.ForeignKey('warehouse_v2.Warehouse', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_STOCK')
    
    qr_id = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Soft deletion field
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.batch_number} | {self.product.name} | {self.current_weight} {self.product.unit}"

class InventoryMovement(models.Model):
    TYPE_CHOICES = (
        ('IN', 'Kirim (In)'),
        ('OUT', 'Chiqim (Out)'),
        ('TRANSFER', 'Ko\'chirish (Transfer)'),
        ('ADJUSTMENT', 'Tuzatish (Adjustment)'),
    )
    
    batch = models.ForeignKey(InventoryBatch, on_delete=models.CASCADE, related_name='movements')
    from_location = models.ForeignKey('warehouse_v2.Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='movements_out')
    to_location = models.ForeignKey('warehouse_v2.Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='movements_in')
    
    quantity = models.DecimalField(max_digits=15, decimal_places=3)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    
    reference = models.CharField(max_length=100, blank=True, help_text="e.g., Zames-101, Sale-501, Project-X")
    timestamp = models.DateTimeField(auto_now_add=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.type} | {self.quantity} | Batch: {self.batch.batch_number}"
