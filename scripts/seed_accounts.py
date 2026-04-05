import os
import django

# Set up Django environment before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from finance.models import Account

def seed_accounts():
    accounts = [
        ('1010', 'Naqd kassa (Cash)', 'ASSET'),
        ('1020', 'Bank hisob raqami (Bank)', 'ASSET'),
        ('2010', 'Xom-ashyo ombori (Raw Materials)', 'ASSET'),
        ('2020', 'Yarim tayyor mahsulot (WIP)', 'ASSET'),
        ('2030', 'Tayyor mahsulot ombori (Finished Goods)', 'ASSET'),
        ('4010', 'Mijozlar qarzdorligi (Receivables)', 'ASSET'),
        ('6010', 'Yetkazib beruvchilar qarzi (Payables)', 'LIABILITY'),
        ('9010', 'Sotuvdan daromad (Revenue)', 'INCOME'),
        ('9400', 'Umumiy xarajatlar (Expenses)', 'EXPENSE'),
        ('9410', 'Transport xarajatlari (Transport Expense)', 'EXPENSE'),
        ('6020', 'Haydovchilar bilan hisob-kitob (Payables Driver)', 'LIABILITY'),
        ('9910', 'Ishlab chiqarish xarajatlari (Production Expense)', 'EXPENSE'),
    ]
    
    for code, name, type_val in accounts:
        Account.objects.get_or_create(code=code, defaults={'name': name, 'type': type_val})
        print(f"Account {code} - {name} seeded.")

if __name__ == "__main__":
    seed_accounts()
