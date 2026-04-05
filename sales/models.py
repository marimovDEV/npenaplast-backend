from django.db import models

class Client(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    address = models.CharField(max_length=255, null=True, blank=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return self.name

class SalesOrder(models.Model):
    STATUS_CHOICES = (
        ('NEW', 'New'),
        ('WAITING_PRODUCTION', 'Waiting Production'),
        ('READY', 'Ready'),
        ('SHIPPED', 'Shipped'),
    )

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='NEW')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.client.name}"

class SalesOrderItem(models.Model):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity = models.FloatField()
    price = models.FloatField()

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
