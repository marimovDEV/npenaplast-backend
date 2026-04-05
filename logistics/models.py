from django.db import models
from django.conf import settings

class Delivery(models.Model):
    DESTINATION_TYPE = (
        ('CLIENT', 'Mijoz uchun (Client)'),
        ('PROJECT', 'Ichki loyiha uchun (Project)'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Kutilmoqda (Pending)'),
        ('SENT', 'Yuborildi (Sent)'),
        ('ARRIVED', 'Yetib bordi (Arrived)'),
        ('RECEIVED', 'Qabul qilindi (Received)'),
        ('CANCELLED', 'Bekor qilingan (Cancelled)'),
    )

    type = models.CharField(max_length=10, choices=DESTINATION_TYPE, default='CLIENT')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    destination_client = models.ForeignKey('sales_v2.Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='logistics_deliveries')
    destination_project = models.ForeignKey('projects.ConstructionProject', on_delete=models.SET_NULL, null=True, blank=True, related_name='logistics_deliveries')
    destination_manual = models.CharField(max_length=255, blank=True, help_text="Manual address if needed")
    
    driver_name = models.CharField(max_length=100, blank=True)
    vehicle_number = models.CharField(max_length=50, blank=True)
    
    # Internal references
    invoice = models.ForeignKey('sales_v2.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='logistics_shipments')
    trip = models.ForeignKey('transport.Trip', on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    
    # Timing
    sent_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Soft deletion
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        dest = self.destination_client.name if self.type == 'CLIENT' and self.destination_client else (self.destination_project.name if self.destination_project else 'Manual')
        return f"Delivery {self.id} | {self.get_type_display()} | {dest} | {self.get_status_display()}"

class DeliveryItem(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('warehouse_v2.Material', on_delete=models.CASCADE)
    batch = models.ForeignKey('inventory.InventoryBatch', on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.DecimalField(max_digits=15, decimal_places=3)
    
    def __str__(self):
        return f"{self.quantity} {self.product.unit} of {self.product.name}"
