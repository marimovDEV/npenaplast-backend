from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class Account(models.Model):
    ACCOUNT_TYPES = (
        ('ASSET', 'Asset (Aktiv)'),
        ('LIABILITY', 'Liability (Majburiyat)'),
        ('EQUITY', 'Equity (Sarmoya)'),
        ('INCOME', 'Income (Daromad)'),
        ('EXPENSE', 'Expense (Xarajat)'),
    )
    
    code = models.CharField(max_length=20, unique=True, help_text="Accounting code (e.g., 1010, 5010)")
    name = models.CharField(max_length=250)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.code} - {self.name} ({self.type})"

class Transaction(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    reference_number = models.CharField(max_length=100, blank=True, null=True, help_text="External invoice or document ID")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='finance_transactions')
    
    def __str__(self):
        return f"TX-{self.id} | {self.date.strftime('%Y-%m-%d')} | {self.description[:30]}"

class TransactionEntry(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='entries')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='entries')
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    def clean(self):
        if self.debit > 0 and self.credit > 0:
            raise ValidationError("A single entry cannot have both debit and credit values.")
        if self.debit == 0 and self.credit == 0:
            raise ValidationError("Entry must have either a debit or credit value.")

    def __str__(self):
        type_str = f"DR: {self.debit}" if self.debit > 0 else f"CR: {self.credit}"
        return f"{self.account.name} | {type_str}"

class Expense(models.Model):
    category = models.CharField(max_length=100, help_text="e.g., Fuel, Salary, Transport")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()
    description = models.TextField(blank=True)
    transaction = models.OneToOneField(Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='expense_record')
    related_process = models.CharField(max_length=255, blank=True, help_text="Link to production, delivery, or project")

    def __str__(self):
        return f"{self.category} - {self.amount} ({self.date})"
