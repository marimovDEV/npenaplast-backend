from django.db import models
from django.conf import settings

class WasteCategory(models.Model):
    name = models.CharField(max_length=100)
    norm_percent = models.FloatField(default=5.0, help_text="Ruxsat etilgan chiqindi foizi (batchga nisbatan)")
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Chiqindi turi"
        verbose_name_plural = "Chiqindi turlari"

class WasteTask(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Qabul qilindi'),
        ('PROCESSING', 'Qayta ishlanmoqda'),
        ('COMPLETED', 'Yakunlandi'),
    )

    DEPT_CHOICES = (
        ('CNC', 'CNC Sexi'),
        ('FINISHING', 'Pardozlash Sexi'),
        ('PRODUCTION', 'Ishlab chiqarish (Quyish)'),
        ('WAREHOUSE', 'Ombor'),
        ('OTHER', 'Boshqa'),
    )

    task_number = models.CharField(max_length=50, unique=True, editable=False)
    source_department = models.CharField(max_length=30, choices=DEPT_CHOICES, default='OTHER')
    batch_number = models.CharField(max_length=100, blank=True, null=True)
    
    category = models.ForeignKey(WasteCategory, on_delete=models.SET_NULL, null=True, related_name='tasks')
    weight_kg = models.FloatField(help_text="Chiqindi vazni (kg)")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='waste_tasks')
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    last_started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    total_duration_seconds = models.IntegerField(default=0)

    # Results
    recycled_weight_kg = models.FloatField(default=0, help_text="Qayta ishlangan vazn (kg)")
    loss_weight_kg = models.FloatField(default=0, help_text="Yo'qotilgan/utilizatsiya qilingan vazn (kg)")
    notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.task_number:
            last_task = WasteTask.objects.order_by('-id').first()
            if last_task:
                last_id = int(last_task.task_number.split('-')[1])
                self.task_number = f"CHQ-{str(last_id + 1).zfill(4)}"
            else:
                self.task_number = "CHQ-0001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.task_number} - {self.category.name if self.category else 'Nomalum'}"

    class Meta:
        verbose_name = "Chiqindi vazifasi"
        verbose_name_plural = "Chiqindi vazifalari"
