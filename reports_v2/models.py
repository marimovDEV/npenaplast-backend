from django.db import models
from django.conf import settings

class ReportHistory(models.Model):
    REPORT_TYPES = (
        ('SALES', 'Sotuvlar'),
        ('INVENTORY', 'Ombor'),
        ('PRODUCTION', 'Ishlab chiqarish'),
        ('WASTE', 'Chiqindilar'),
    )
    FORMAT_CHOICES = (
        ('PDF', 'PDF'),
        ('EXCEL', 'Excel'),
    )
    STATUS_CHOICES = (
        ('PENDING', 'Tayyorlanmoqda'),
        ('READY', 'Tayyor'),
        ('ERROR', 'Xato'),
    )

    name = models.CharField(max_length=255)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    period = models.CharField(max_length=100) # e.g. "2026-03-01 - 2026-03-27"
    file_format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    file_size = models.CharField(max_length=20, default='0 KB')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='READY')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    file_path = models.FileField(upload_to='reports/', null=True, blank=True)

    def __str__(self):
        return self.name
