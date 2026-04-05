from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    ACTION_CHOICES = (
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('STATUS_CHANGE', 'Status Change'),
        ('STOCK_MOVE', 'Stock Move'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    module = models.CharField(max_length=50) # e.g. "Inventory", "Documents"
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    object_id = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"[{self.module}] {self.user} - {self.action}: {self.description[:50]}"

    class Meta:
        ordering = ['-timestamp']
