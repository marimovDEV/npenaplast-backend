import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact_info = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class Material(models.Model):
    # Shared material/product model
    CATEGORY_CHOICES = (
        ('RAW', 'Xom-ashyo'),
        ('SEMI', 'Yarim tayyor mahsulot'),
        ('FINISHED', 'Tayyor mahsulot'),
        ('OTHER', 'Boshqa'),
    )
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=50, unique=True, null=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OTHER')
    unit = models.CharField(max_length=20, default='kg')
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name

class RawMaterialBatch(models.Model):
    STATUS_CHOICES = (
        ('RECEIVED', 'Qabul qilindi'),
        ('INSPECTION', 'Tekshiruvda'),
        ('IN_STOCK', 'Omborda'),
        ('RESERVED', 'Band qilingan'),
        ('DEPLETED', 'Tugatilgan'),
        ('CANCELLED', 'Bekor qilindi'),
    )
    invoice_number = models.CharField(max_length=100)
    supplier_name = models.CharField(max_length=255, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='batches', null=True, blank=True)
    date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField(null=True, blank=True)
    quantity_kg = models.FloatField()
    remaining_quantity = models.FloatField(default=0)
    reserved_quantity = models.FloatField(default=0)
    batch_number = models.CharField(max_length=100, unique=True)
    price_per_unit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='UZS')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_STOCK')
    qr_code = models.UUIDField(default=uuid.uuid4, editable=False)
    responsible_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    material = models.ForeignKey(Material, on_delete=models.CASCADE, null=True)

    @property
    def qr_content(self):
        """Structured QR data for Industrial ERP Scanning"""
        return f"BAT:{self.batch_number}"

    def __str__(self):
        return f"Batch {self.batch_number} - {self.material.name}"

class Warehouse(models.Model):
    name = models.CharField(max_length=100) # Sklad 1, 2, 3, 4
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Stock(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    quantity = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('warehouse', 'material')

    def __str__(self):
        return f"{self.warehouse.name}: {self.material.name} ({self.quantity})"

class WarehouseTransfer(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Kutilmoqda'),
        ('COMPLETED', 'Yakunlandi'),
        ('CANCELLED', 'Bekor qilindi'),
    )
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='outgoing_transfers')
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='incoming_transfers')
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    quantity = models.FloatField()
    date = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='COMPLETED')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Transfer {self.quantity} {self.material.name} from {self.from_warehouse} to {self.to_warehouse} ({self.status})"

class BatchReservation(models.Model):
    document = models.ForeignKey('documents.Document', on_delete=models.CASCADE, related_name='reservations')
    batch = models.ForeignKey(RawMaterialBatch, on_delete=models.CASCADE, related_name='reservations')
    quantity = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reservation: {self.quantity} from {self.batch.batch_number} for {self.document.number}"

# ═══════════════════════════════════════════════════
# PHASE 3: INVENTORY RECONCILIATION
# ═══════════════════════════════════════════════════

class InventoryAudit(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Qoralama'
        IN_PROGRESS = 'IN_PROGRESS', 'Sanalyapti'
        REVIEW = 'REVIEW', 'Tasdiqlash kutilmoqda'
        COMPLETED = 'COMPLETED', 'Yakunlangan'
    
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    auditor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='audits_conducted')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audits_approved')
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sklad Auditi'
        verbose_name_plural = 'Sklad Auditlari'

    def __str__(self):
        return f"Audit: {self.warehouse.name} - {self.date}"

class InventoryAuditLine(models.Model):
    audit = models.ForeignKey(InventoryAudit, on_delete=models.CASCADE, related_name='lines')
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    system_qty = models.FloatField(help_text="Tizimdagi qoldiq")
    actual_qty = models.FloatField(help_text="Haqiqiy sanalgan qoldiq", null=True, blank=True)
    
    @property
    def variance(self):
        if self.actual_qty is None:
            return 0
        return self.actual_qty - self.system_qty

    def __str__(self):
        return f"{self.material.name}: Sys {self.system_qty} vs Act {self.actual_qty}"
