from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    ACTION_CHOICES = (
        ('CREATE', 'Yaratish'),
        ('UPDATE', 'Tahrirlash'),
        ('DELETE', 'O\'chirish'),
        ('LOGIN', 'Kirish'),
        ('LOGOUT', 'Chiqish'),
        ('TRANSFER', 'O\'tkazma'),
        ('ERROR', 'Xatolik'),
    )

    STATUS_CHOICES = (
        ('SUCCESS', 'Muvaffaqiyatli'),
        ('ERROR', 'Xatolik'),
        ('WARNING', 'Ogohlantirish'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    module = models.CharField(max_length=50) 
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    object_id = models.CharField(max_length=100, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='SUCCESS')

    # Enterprise Audit Fields (NEW)
    old_value = models.JSONField(null=True, blank=True, help_text="O'zgarishdan oldingi qiymat")
    new_value = models.JSONField(null=True, blank=True, help_text="O'zgarishdan keyingi qiymat")
    model_name = models.CharField(max_length=100, null=True, blank=True, help_text="Model nomi (masalan: Invoice)")

    def __str__(self):
        return f"[{self.module}] {self.user} - {self.action}: {self.description[:50]}"

    class Meta:
        ordering = ['-timestamp']

class Notification(models.Model):
    TYPE_CHOICES = (
        ('INFO', 'Ma\'lumot'),
        ('WARNING', 'Ogohlantirish'),
        ('ERROR', 'Xatolik'),
        ('SUCCESS', 'Muvaffaqiyatli'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='INFO')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {self.title}"

    class Meta:
        ordering = ['-created_at']
