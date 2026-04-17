"""
Budgets & Cost Control Models
"""

from django.db import models
from accounting.models import Account, FiscalPeriod
from django.core.exceptions import ValidationError

class CostCenter(models.Model):
    """Xarajat markazi (Department / Bo'lim)."""
    name = models.CharField(max_length=150, help_text="Masalan: Ishlab chiqarish, Logistika")
    code = models.CharField(max_length=50, unique=True, help_text="CC-001")
    manager = models.ForeignKey(
        'accounts.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='managed_cost_centers'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Xarajat Markazi'
        verbose_name_plural = 'Xarajat Markazlari'

    def __str__(self):
        return f"{self.code} - {self.name}"

class Budget(models.Model):
    """
    Kutilayotgan byudjet / cheklovlar.
    Planned vs Actual comparison.
    """
    class StatusChoices(models.TextChoices):
        DRAFT = 'DRAFT', 'Qoralama'
        ACTIVE = 'ACTIVE', 'Faol'
        CLOSED = 'CLOSED', 'Yopilgan'

    name = models.CharField(max_length=200, help_text="Masalan: 2026 Aprel Logistika Byudjeti")
    fiscal_period = models.ForeignKey(FiscalPeriod, on_delete=models.CASCADE)
    cost_center = models.ForeignKey(CostCenter, on_delete=models.CASCADE, null=True, blank=True)
    account = models.ForeignKey(
        Account, 
        on_delete=models.CASCADE,
        help_text="Qaysi xarajat hisobi uchun (majburiy emas)"
    )
    
    planned_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    actual_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0, help_text="Avto hisoblanadi")
    
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Byudjet'
        verbose_name_plural = 'Byudjetlar'
        unique_together = ('fiscal_period', 'account', 'cost_center')

    def __str__(self):
        return self.name

    @property
    def variance(self):
        """Variance: positive is good (under budget), negative is bad (over budget) for expenses."""
        return self.planned_amount - self.actual_amount

    @property
    def used_percentage(self):
        if self.planned_amount == 0:
            return 100 if self.actual_amount > 0 else 0
        return (self.actual_amount / self.planned_amount) * 100

class TrueCostEstimation(models.Model):
    """
    Haqiqiy mahsulot tannarxi hisobi.
    Har bir zames yoki blok partiyasi uchun.
    """
    production_type = models.CharField(max_length=50, help_text="ZAMES, BLOCK")
    reference_id = models.CharField(max_length=50, help_text="Zames ID yoki BlockProduction ID")
    
    material_cost = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    labor_cost = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    energy_cost = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    overhead_cost = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_cost(self):
        return self.material_cost + self.labor_cost + self.energy_cost + self.overhead_cost

    def __str__(self):
        return f"{self.production_type} #{self.reference_id} - {self.total_cost}"
