from django.utils import timezone
from .models import WasteTask, WasteCategory
from django.db import transaction

def accept_waste(source_department, weight_kg, category_id, batch_number=None, operator=None):
    """
    Ishlab chiqarishdan chiqindini qabul qilish.
    """
    if weight_kg <= 0:
        raise ValueError("weight_kg 0 dan katta bo'lishi kerak.")
    category = WasteCategory.objects.get(id=category_id)
    task = WasteTask.objects.create(
        source_department=source_department,
        weight_kg=weight_kg,
        category=category,
        batch_number=batch_number,
        operator=operator,
        status='PENDING'
    )
    return task

def start_processing_waste(task_id):
    """
    Chiqindini qayta ishlashni boshlash (taymer yoqiladi).
    """
    task = WasteTask.objects.get(id=task_id)
    if task.status == 'COMPLETED':
        raise ValueError("Bu vazifa allaqachon yakunlangan.")
    if task.status == 'PROCESSING':
        return task
    
    task.status = 'PROCESSING'
    task.last_started_at = timezone.now()
    task.save()
    return task

def finish_processing_waste(task_id, recycled_weight_kg, loss_weight_kg, notes=None):
    """
    Chiqindini qayta ishlashni yakunlash.
    """
    with transaction.atomic():
        task = WasteTask.objects.get(id=task_id)
        if recycled_weight_kg < 0 or loss_weight_kg < 0:
            raise ValueError("recycled_weight_kg va loss_weight_kg manfiy bo'lishi mumkin emas.")
        if recycled_weight_kg + loss_weight_kg > task.weight_kg:
            raise ValueError("Qayta ishlangan va yo'qotilgan vazn jami qabul qilingan chiqindidan oshib ketdi.")
        if task.status != 'PROCESSING':
            # Agar hali boshlanmagan bo'lsa, avtomatik boshlash va tugatish
            if not task.last_started_at:
                task.last_started_at = timezone.now()
        
        # Vaqtni hisoblash
        now = timezone.now()
        elapsed = int((now - task.last_started_at).total_seconds())
        task.total_duration_seconds += elapsed
        
        task.status = 'COMPLETED'
        task.finished_at = now
        task.recycled_weight_kg = recycled_weight_kg
        task.loss_weight_kg = loss_weight_kg
        task.notes = notes
        task.save()
        
        # Bu yerda kelajakda omborga qayta ishlangan mahsulotni qo'shish logikasi bo'lishi mumkin
        
    return task

def create_waste_task(source, material, weight, user=None):
    """
    Creates a WasteTask from an external source (e.g. QC rejection).
    Used by production_v2.services.perform_quality_check.
    """
    # Find or create a default waste category for QC rejects
    category, _ = WasteCategory.objects.get_or_create(
        name='Brak (QC)',
        defaults={'norm_percent': 3.0, 'description': 'Sifat nazoratidan o\'tmagan'}
    )
    
    task = WasteTask.objects.create(
        source_department='PRODUCTION',
        weight_kg=weight,
        category=category,
        batch_number=source,
        operator=user,
        status='PENDING'
    )
    return task

def get_waste_stats():
    """
    Asosiy statistikalarni olish.
    """
    from django.db.models import Sum, Count
    today = timezone.now().date()
    
    stats = {
        'today_total': WasteTask.objects.filter(created_at__date=today).aggregate(Sum('weight_kg'))['weight_kg__sum'] or 0,
        'active_tasks': WasteTask.objects.filter(status='PROCESSING').count(),
        'pending_tasks': WasteTask.objects.filter(status='PENDING').count(),
        'by_category': WasteTask.objects.values('category__name').annotate(total=Sum('weight_kg')).order_by('-total')
    }
    return stats
