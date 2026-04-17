"""
Alerts & Notifications Models
"""

from django.db import models
from django.conf import settings

class AlertRule(models.Model):
    """
    Qachon alert yuborish kerakligini belgilovchi qoida.
    Masalan: Xom ashyo kamqolsa, Minus balans kuzatilsa.
    """
    class TriggerType(models.TextChoices):
        LOW_STOCK = 'LOW_STOCK', 'Sklad kamayishi'
        NEGATIVE_BALANCE = 'NEGATIVE_BALANCE', 'Minus balans'
        BUDGET_EXCEEDED = 'BUDGET_EXCEEDED', 'Byudjet oshib ketishi'
        COMPLIANCE_VIOLATION = 'COMPLIANCE_VIOLATION', 'Qoida buzilishi'
        LARGE_TRANSACTION = 'LARGE_TRANSACTION', 'Katta summa tranzaksiyasi'

    name = models.CharField(max_length=200)
    trigger_type = models.CharField(max_length=50, choices=TriggerType.choices)
    threshold = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, help_text="Chegara qiymati (limit)")
    is_active = models.BooleanField(default=True)
    
    # Kimlarga boradi (rollar yoki Userlar bo'lishi mumkin)
    recipients = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='alert_rules')

    def __str__(self):
        return f"{self.name} ({self.trigger_type})"


class Alert(models.Model):
    """Joriy alert xabari."""
    class Severity(models.TextChoices):
        INFO = 'INFO', 'Ma\'lumot'
        WARNING = 'WARNING', 'Ogohlantirish'
        CRITICAL = 'CRITICAL', 'Kritik'

    rule = models.ForeignKey(AlertRule, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO)
    
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.severity}] {self.title}"

class SmartAnomalyRule(models.Model):
    """
    ANOMALY DETECTION (SMART CONTROL) e.g., abnormal waste %, abnormal expense burst.
    """
    class AnomalyType(models.TextChoices):
        PROD_LOSS = 'PROD_LOSS', 'Ishlab chiqarish brak darajasi'
        PRICE_DUMP = 'PRICE_DUMP', 'Narxning keskin tushishi'
        EXPENSE_SPIKE = 'EXPENSE_SPIKE', 'Kutilmagan katta xarajat'
        STRANGE_TIME = 'STRANGE_TIME', 'Tunda/Dam olish kunida operatsiya'

    name = models.CharField(max_length=200)
    anomaly_type = models.CharField(max_length=50, choices=AnomalyType.choices)
    normal_threshold = models.DecimalField(max_digits=18, decimal_places=2, help_text="Odatdagi chegara (masalan % yoki summa)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Anomaly: {self.name} ({self.anomaly_type})"
