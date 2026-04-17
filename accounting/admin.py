from django.contrib import admin
from .models import Account, JournalEntry, JournalEntryLine, FiscalPeriod, TaxRate


class JournalEntryLineInline(admin.TabularInline):
    model = JournalEntryLine
    extra = 2


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'account_type', 'balance', 'is_active', 'is_system']
    list_filter = ['account_type', 'is_active', 'is_system']
    search_fields = ['code', 'name']
    ordering = ['code']


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['entry_number', 'date', 'description', 'status', 'total_amount', 'source_type']
    list_filter = ['status', 'source_type', 'date']
    search_fields = ['entry_number', 'description']
    inlines = [JournalEntryLineInline]
    readonly_fields = ['entry_number', 'posted_at', 'voided_at']


@admin.register(FiscalPeriod)
class FiscalPeriodAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_closed']
    list_filter = ['is_closed']


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'rate', 'is_active']
    list_filter = ['is_active']
