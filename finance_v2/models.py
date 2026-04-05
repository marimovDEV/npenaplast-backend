from django.db import models
from django.db import transaction
from django.conf import settings
from django.core.exceptions import ValidationError

class Cashbox(models.Model):
    TYPE_CHOICES = (
        ('CASH', 'Naqd kassa'),
        ('BANK', 'Bank hisobi (Perezichleniya)'),
        ('CARD', 'Karta (Humo/Uzcard)'),
    )
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='CASH')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    branch = models.CharField(max_length=100, default="Asosiy Filial")
    responsible_person = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_cashboxes')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_type_display()}) - {self.balance}"

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class FinancialTransaction(models.Model):
    TYPE_CHOICES = (
        ('INCOME', 'Kirim (In)'),
        ('EXPENSE', 'Chiqim (Out)'),
    )
    DEPT_CHOICES = (
        ('ADMIN', 'Administratsiya'),
        ('PRODUCTION', 'Ishlab chiqarish'),
        ('LOGISTICS', 'Logistika'),
        ('SALES', 'Sotuv'),
        ('OTHER', 'Boshqa'),
    )
    cashbox = models.ForeignKey(Cashbox, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    department = models.CharField(max_length=20, choices=DEPT_CHOICES, default='OTHER')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True)
    customer = models.ForeignKey('sales_v2.Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='finance_history')
    description = models.TextField(blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    attachment = models.FileField(upload_to='finance/attachments/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.amount is None or self.amount <= 0:
            raise ValidationError({'amount': "Miqdor 0 dan katta bo'lishi kerak."})

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not is_new:
            self.full_clean()
            return super().save(*args, **kwargs)

        with transaction.atomic():
            self.full_clean()
            cashbox = Cashbox.objects.select_for_update().get(pk=self.cashbox_id)

            if self.type == 'EXPENSE' and cashbox.balance < self.amount:
                raise ValidationError({'amount': "Kassada mablag' yetarli emas."})

            if self.type == 'INCOME':
                cashbox.balance += self.amount
            else:
                cashbox.balance -= self.amount
            cashbox.save(update_fields=['balance'])
            self.cashbox = cashbox

            if self.customer:
                balance, _ = ClientBalance.objects.get_or_create(customer=self.customer)
                balance = ClientBalance.objects.select_for_update().get(pk=balance.pk)
                if self.type == 'INCOME':
                    balance.total_debt -= self.amount
                else:
                    balance.total_debt += self.amount
                balance.save(update_fields=['total_debt', 'last_updated'])

            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.type}: {self.amount} via {self.cashbox.name}"

class InternalTransfer(models.Model):
    from_cashbox = models.ForeignKey(Cashbox, on_delete=models.CASCADE, related_name='transfers_out')
    to_cashbox = models.ForeignKey(Cashbox, on_delete=models.CASCADE, related_name='transfers_in')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.amount is None or self.amount <= 0:
            raise ValidationError({'amount': "Miqdor 0 dan katta bo'lishi kerak."})
        if self.from_cashbox_id and self.to_cashbox_id and self.from_cashbox_id == self.to_cashbox_id:
            raise ValidationError("Pulni bir xil kassaning o'ziga o'tkazib bo'lmaydi.")

    def save(self, *args, **kwargs):
        if self.pk:
            self.full_clean()
            return super().save(*args, **kwargs)

        with transaction.atomic():
            self.full_clean()
            from_cashbox = Cashbox.objects.select_for_update().get(pk=self.from_cashbox_id)
            to_cashbox = Cashbox.objects.select_for_update().get(pk=self.to_cashbox_id)

            if from_cashbox.balance < self.amount:
                raise ValidationError({'amount': "O'tkazma uchun kassada mablag' yetarli emas."})

            from_cashbox.balance -= self.amount
            to_cashbox.balance += self.amount
            from_cashbox.save(update_fields=['balance'])
            to_cashbox.save(update_fields=['balance'])

            self.from_cashbox = from_cashbox
            self.to_cashbox = to_cashbox
            super().save(*args, **kwargs)

class ClientBalance(models.Model):
    customer = models.OneToOneField('sales_v2.Customer', on_delete=models.CASCADE, related_name='balance')
    total_debt = models.DecimalField(max_digits=15, decimal_places=2, default=0) # Negative means we owe them
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer.name}: {self.total_debt}"
