from django.db import models

class Inventory(models.Model):
    product = models.ForeignKey('warehouse_v2.Material', on_delete=models.CASCADE)
    warehouse = models.ForeignKey('warehouse_v2.Warehouse', on_delete=models.CASCADE)
    quantity = models.FloatField(default=0)
    reserved_quantity = models.FloatField(default=0) # Stock allocated to orders
    batch_number = models.CharField(max_length=100, null=True, blank=True)
    supplier = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Inventories"
        unique_together = ('product', 'warehouse', 'batch_number')

    def __str__(self):
        return f"{self.product.name} ({self.batch_number}) @ {self.warehouse.name}: {self.quantity}"
