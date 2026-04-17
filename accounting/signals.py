"""
Accounting Signals — ERP Event → Avtomatik Provodka

Har bir ERP operatsiyasi avtomatik ravishda buxgalteriya yozuvini yaratadi:

1. Xom ashyo kirim (RawMaterialBatch.status → IN_STOCK):
   DR: 1010 (Xom ashyo)      CR: 6700 (Mol yetkazib beruvchilar)

2. Ishlab chiqarish (Zames.status → DONE):
   DR: 2010 (Ishlab chiqarish xarajatlari)   CR: 1010 (Xom ashyo)

3. Tayyor mahsulot (BlockProduction.status → READY):
   DR: 2810 (Tayyor mahsulot)    CR: 2010 (Ishlab chiqarish)

4. Sotuv (Invoice.status → CONFIRMED):
   DR: 4810 (Xaridorlar)         CR: 9010 (Sotuv daromadi)
   DR: 9100 (Sotuv tannarxi)     CR: 2810 (Tayyor mahsulot)

5. To'lov qabul qilish (FinancialTransaction.type → INCOME):
   DR: 5010/5020 (Kassa/Bank)    CR: 4810 (Xaridorlar)

6. Xarajat to'lovi (FinancialTransaction.type → EXPENSE):
   DR: 9200+ (Xarajat)           CR: 5010/5020 (Kassa/Bank)
"""

import logging
from decimal import Decimal
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════
# FINAL ENTERPRISE HARDENING: PERIOD LOCK PROTECTION
# ═══════════════════════════════════════════════════

@receiver(pre_save, sender='accounting.JournalEntry')
def prevent_closed_period_modifications(sender, instance, **kwargs):
    """Davr yopilgandan keyin provodkalarni o'zgartirishni taqiqlash."""
    if instance.pk:
        # Avoid direct import at top level to prevent circular imports if needed, but it's safe here
        from .models import JournalEntry
        try:
            old_instance = JournalEntry.objects.get(pk=instance.pk)
            if old_instance.fiscal_period and old_instance.fiscal_period.is_closed:
                raise ValidationError("FINAL ENTERPRISE: Yopilgan davrdagi provodkani o'zgartirish qat'iyan man etiladi.")
        except JournalEntry.DoesNotExist:
            pass

@receiver(pre_delete, sender='accounting.JournalEntry')
def prevent_closed_period_deletions(sender, instance, **kwargs):
    if instance.fiscal_period and instance.fiscal_period.is_closed:
        raise ValidationError("FINAL ENTERPRISE: Yopilgan davrdagi provodkani o'chirish qat'iyan man etiladi.")

@receiver(pre_save, sender='accounting.JournalEntryLine')
def prevent_closed_period_line_modifications(sender, instance, **kwargs):
    if instance.journal_entry_id:
        from .models import JournalEntry
        entry = JournalEntry.objects.get(pk=instance.journal_entry_id)
        if entry.fiscal_period and entry.fiscal_period.is_closed:
            raise ValidationError("FINAL ENTERPRISE: Yopilgan davrdagi provodka qatorini o'zgartirish mumkin emas.")

@receiver(pre_delete, sender='accounting.JournalEntryLine')
def prevent_closed_period_line_deletions(sender, instance, **kwargs):
    from .models import JournalEntry
    entry = JournalEntry.objects.get(pk=instance.journal_entry_id)
    if entry.fiscal_period and entry.fiscal_period.is_closed:
        raise ValidationError("FINAL ENTERPRISE: Yopilgan davrdagi provodka qatorini o'chirish mumkin emas.")




def _safe_create_entry(description, lines, source_type, source_id, source_description='', user=None):
    """Xavfsiz provodka yaratish — xatolikda tizimni to'xtatmaydi."""
    try:
        from .services import create_journal_entry
        from .models import Account

        # Validate all accounts exist before creating
        for line in lines:
            code = line.get('account_code')
            if code and not Account.objects.filter(code=code, is_active=True).exists():
                logger.warning(
                    f"Accounting signal skipped: Account {code} not found. "
                    f"Source: {source_type} #{source_id}"
                )
                return None

        entry = create_journal_entry(
            description=description,
            lines=lines,
            source_type=source_type,
            source_id=source_id,
            source_description=source_description,
            user=user,
            auto_post=True,
        )
        logger.info(f"✅ Auto provodka: {entry.entry_number} — {description}")
        return entry
    except Exception as e:
        logger.error(f"❌ Accounting signal error: {e} | Source: {source_type} #{source_id}")
        return None


# ═══════════════════════════════════════════════════
# 1. XOM ASHYO KIRIM (Warehouse)
# ═══════════════════════════════════════════════════

@receiver(post_save, sender='warehouse_v2.RawMaterialBatch')
def on_raw_material_received(sender, instance, created, **kwargs):
    """
    Xom ashyo omborga kirganda:
    DR: 1010 (Xom ashyo)           — aktiv oshadi
    CR: 6700 (Mol yetkazib beruvchilar) — majburiyat oshadi
    """
    if not created:
        return

    if instance.status not in ('RECEIVED', 'IN_STOCK'):
        return

    amount = Decimal(str(instance.quantity_kg)) * instance.price_per_unit
    if amount <= 0:
        return

    _safe_create_entry(
        description=f"Xom ashyo kirim: Partiya {instance.batch_number} "
                    f"({instance.quantity_kg} kg × {instance.price_per_unit})",
        lines=[
            {
                'account_code': '1010',
                'debit': amount,
                'credit': 0,
                'description': f"Xom ashyo: {instance.material.name if instance.material else 'N/A'}",
            },
            {
                'account_code': '6700',
                'debit': 0,
                'credit': amount,
                'description': f"Yetkazib beruvchi: {instance.supplier_name or 'N/A'}",
            },
        ],
        source_type='WAREHOUSE',
        source_id=instance.id,
        source_description=f"RawMaterialBatch #{instance.id}",
        user=instance.responsible_user,
    )


# ═══════════════════════════════════════════════════
# 2. ISHLAB CHIQARISH (Production — Zames)
# ═══════════════════════════════════════════════════

@receiver(post_save, sender='production_v2.Zames')
def on_zames_completed(sender, instance, **kwargs):
    """
    Zames tugaganda (status=DONE):
    DR: 2010 (Ishlab chiqarish xarajatlari)  — xarajat oshadi
    CR: 1010 (Xom ashyo)                     — aktiv kamayadi
    """
    if instance.status != 'DONE':
        return

    # Calculate material cost from zames items
    total_cost = Decimal('0')
    for item in instance.items.all():
        if item.batch and item.batch.price_per_unit:
            total_cost += Decimal(str(item.quantity)) * item.batch.price_per_unit
        elif item.material and item.material.price:
            total_cost += Decimal(str(item.quantity)) * item.material.price

    if total_cost <= 0:
        # Fallback: use input_weight * average price
        if instance.input_weight > 0:
            total_cost = Decimal(str(instance.input_weight)) * Decimal('1000')  # default est.

    if total_cost <= 0:
        return

    _safe_create_entry(
        description=f"Ishlab chiqarish: Zames {instance.zames_number} "
                    f"(material sarfi: {total_cost:,.0f} so'm)",
        lines=[
            {
                'account_code': '2010',
                'debit': total_cost,
                'credit': 0,
                'description': f"Zames {instance.zames_number} ishlab chiqarish xarajati",
            },
            {
                'account_code': '1010',
                'debit': 0,
                'credit': total_cost,
                'description': f"Material sarfi: Zames {instance.zames_number}",
            },
        ],
        source_type='PRODUCTION',
        source_id=instance.id,
        source_description=f"Zames #{instance.zames_number}",
        user=instance.operator,
    )


# ═══════════════════════════════════════════════════
# 3. TAYYOR MAHSULOT (BlockProduction → READY)
# ═══════════════════════════════════════════════════

@receiver(post_save, sender='production_v2.BlockProduction')
def on_block_ready(sender, instance, **kwargs):
    """
    Blok tayyor bo'lganda (status=READY):
    DR: 2810 (Tayyor mahsulot)               — aktiv oshadi
    CR: 2010 (Ishlab chiqarish xarajatlari)  — xarajat kamayadi
    """
    if instance.status != 'READY':
        return

    # Estimate product value from volume and density
    volume_m3 = instance.volume or 0
    if volume_m3 <= 0:
        return

    # Estimate cost based on material price or default
    estimated_cost = Decimal(str(volume_m3)) * Decimal('50000')  # so'm per m3 default

    _safe_create_entry(
        description=f"Tayyor mahsulot: {instance.block_count} blok "
                    f"({volume_m3:.2f} m³, {instance.density} kg/m³)",
        lines=[
            {
                'account_code': '2810',
                'debit': estimated_cost,
                'credit': 0,
                'description': f"Blok: Form {instance.form_number}, {instance.block_count} dona",
            },
            {
                'account_code': '2010',
                'debit': 0,
                'credit': estimated_cost,
                'description': f"Ishlab chiqarish tannarxi",
            },
        ],
        source_type='PRODUCTION',
        source_id=instance.id,
        source_description=f"BlockProduction #{instance.id}",
    )


# ═══════════════════════════════════════════════════
# 4. SOTUV (Invoice → CONFIRMED)
# ═══════════════════════════════════════════════════

@receiver(post_save, sender='sales_v2.Invoice')
def on_invoice_confirmed(sender, instance, **kwargs):
    """
    Faktura tasdiqlanganda (status=CONFIRMED):

    1-provodka (Daromad):
    DR: 4810 (Xaridorlar — debitorlik)   — aktiv oshadi
    CR: 9010 (Sotuv daromadi)             — daromad oshadi

    (QQS uchun):
    CR: 6410 (QQS)                        — soliq majburiyati
    """
    if instance.status != 'CONFIRMED':
        return

    total = instance.total_amount
    if not total or total <= 0:
        return

    # Calculate VAT (12%)
    vat_amount = (Decimal(str(total)) * Decimal('12')) / Decimal('112')
    net_amount = Decimal(str(total)) - vat_amount

    lines = [
        {
            'account_code': '4810',
            'debit': Decimal(str(total)),
            'credit': 0,
            'description': f"Xaridor: {instance.customer.name if instance.customer else 'N/A'}",
        },
        {
            'account_code': '9010',
            'debit': 0,
            'credit': net_amount,
            'description': f"Sotuv daromadi (QQS siz)",
        },
        {
            'account_code': '6410',
            'debit': 0,
            'credit': vat_amount,
            'description': f"QQS 12%",
        },
    ]

    _safe_create_entry(
        description=f"Sotuv: Faktura {instance.invoice_number} — {total:,.0f} so'm "
                    f"(QQS: {vat_amount:,.0f})",
        lines=lines,
        source_type='SALE',
        source_id=instance.id,
        source_description=f"Invoice #{instance.invoice_number}",
        user=instance.created_by,
    )


# ═══════════════════════════════════════════════════
# 5. MOLIYA OPERATSIYALARI (FinancialTransaction)
# ═══════════════════════════════════════════════════

@receiver(post_save, sender='finance_v2.FinancialTransaction')
def on_financial_transaction(sender, instance, created, **kwargs):
    """
    Pul kirim/chiqim:

    INCOME (Kirim):
    DR: 5010/5020 (Kassa/Bank)    CR: 4810 (Xaridorlar) yoki 9030 (Boshqa daromad)

    EXPENSE (Chiqim):
    DR: 9220 (Ma'muriy xarajat) yoki kategoriyaga mos   CR: 5010/5020 (Kassa/Bank)
    """
    if not created:
        return

    amount = Decimal(str(instance.amount))
    if amount <= 0:
        return

    # Determine cash account based on cashbox type
    cashbox_type = instance.cashbox.type if instance.cashbox else 'CASH'
    cash_account = '5010' if cashbox_type == 'CASH' else '5020'

    if instance.type == 'INCOME':
        # If from customer → reduce receivable, else → other income
        credit_account = '4810' if instance.customer else '9030'
        credit_desc = f"Xaridor: {instance.customer.name}" if instance.customer else "Boshqa daromad"

        _safe_create_entry(
            description=f"Pul kirim: {amount:,.0f} so'm — {instance.description or 'N/A'}",
            lines=[
                {
                    'account_code': cash_account,
                    'debit': amount,
                    'credit': 0,
                    'description': f"Kirim: {instance.cashbox.name}",
                },
                {
                    'account_code': credit_account,
                    'debit': 0,
                    'credit': amount,
                    'description': credit_desc,
                },
            ],
            source_type='FINANCE',
            source_id=instance.id,
            source_description=f"FinancialTransaction #{instance.id}",
            user=instance.performed_by,
        )

    elif instance.type == 'EXPENSE':
        # Map department to expense account
        dept_account_map = {
            'ADMIN': '9220',          # Ma'muriy xarajat
            'PRODUCTION': '2500',     # Umumishlab chiqarish
            'LOGISTICS': '9210',      # Sotish xarajatlari
            'SALES': '9210',          # Sotish xarajatlari
            'OTHER': '9230',          # Boshqa xarajatlar
        }
        expense_account = dept_account_map.get(instance.department, '9230')

        _safe_create_entry(
            description=f"Xarajat: {amount:,.0f} so'm — {instance.description or 'N/A'}",
            lines=[
                {
                    'account_code': expense_account,
                    'debit': amount,
                    'credit': 0,
                    'description': f"Xarajat: {instance.description or 'N/A'}",
                },
                {
                    'account_code': cash_account,
                    'debit': 0,
                    'credit': amount,
                    'description': f"Chiqim: {instance.cashbox.name}",
                },
            ],
            source_type='FINANCE',
            source_id=instance.id,
            source_description=f"FinancialTransaction #{instance.id}",
            user=instance.performed_by,
        )


# ═══════════════════════════════════════════════════
# 6. ICHKI O'TKAZMA (InternalTransfer)
# ═══════════════════════════════════════════════════

@receiver(post_save, sender='finance_v2.InternalTransfer')
def on_internal_transfer(sender, instance, created, **kwargs):
    """
    Kassalar orasidagi o'tkazma:
    DR: Target kassa hisob     CR: Source kassa hisob
    """
    if not created:
        return

    amount = Decimal(str(instance.amount))
    if amount <= 0:
        return

    from_type = instance.from_cashbox.type if instance.from_cashbox else 'CASH'
    to_type = instance.to_cashbox.type if instance.to_cashbox else 'CASH'

    from_account = '5010' if from_type == 'CASH' else '5020'
    to_account = '5010' if to_type == 'CASH' else '5020'

    if from_account == to_account:
        # Same account type — use transit account
        _safe_create_entry(
            description=f"Ichki o'tkazma: {instance.from_cashbox.name} → {instance.to_cashbox.name} "
                        f"({amount:,.0f} so'm)",
            lines=[
                {
                    'account_code': '5050',  # O'tkazmalardagi pul
                    'debit': amount,
                    'credit': 0,
                    'description': f"O'tkazma: {instance.from_cashbox.name} dan",
                },
                {
                    'account_code': '5050',
                    'debit': 0,
                    'credit': amount,
                    'description': f"O'tkazma: {instance.to_cashbox.name} ga",
                },
            ],
            source_type='TRANSFER',
            source_id=instance.id,
            source_description=f"InternalTransfer #{instance.id}",
            user=instance.performed_by,
        )
    else:
        _safe_create_entry(
            description=f"Ichki o'tkazma: {instance.from_cashbox.name} → {instance.to_cashbox.name} "
                        f"({amount:,.0f} so'm)",
            lines=[
                {
                    'account_code': to_account,
                    'debit': amount,
                    'credit': 0,
                    'description': f"Kirim: {instance.to_cashbox.name}",
                },
                {
                    'account_code': from_account,
                    'debit': 0,
                    'credit': amount,
                    'description': f"Chiqim: {instance.from_cashbox.name}",
                },
            ],
            source_type='TRANSFER',
            source_id=instance.id,
            source_description=f"InternalTransfer #{instance.id}",
            user=instance.performed_by,
        )

# ═══════════════════════════════════════════════════
# 7. PRODUCTION BATCH COST FINALIZATION (Phase 4)
# ═══════════════════════════════════════════════════

@receiver(post_save, sender='production_v2.ProductionBatch')
def on_production_batch_closed(sender, instance, **kwargs):
    """
    Batch yopilganda (status=CLOSED):
    DR: 2810 (Tayyor mahsulot)  - Real tannarxda
    CR: 1010 (Xom ashyo)        - Materiallar qismi
    CR: 9200 (Boshqa xarajatlar) - Energiya, Mehnat, Overheadlar
    """
    if instance.status != 'CLOSED' or instance.total_cost <= 0:
        return

    # Check if entry already exists to prevent duplicates
    from .models import JournalEntry
    if JournalEntry.objects.filter(source_type='PRODUCTION', source_id=instance.id).exists():
        return

    lines = [
        {
            'account_code': '2810', # Tayyor mahsulot
            'debit': instance.total_cost,
            'credit': 0,
            'description': f"Tayyor mahsulot tannarxi: Batch {instance.batch_number}",
        },
        {
            'account_code': '1010', # Xom ashyo
            'debit': 0,
            'credit': instance.material_cost,
            'description': f"Material sarfi: Batch {instance.batch_number}",
        },
    ]

    # Add other cost components to credit
    other_costs = [
        ('9220', instance.energy_cost, "Energiya (Gaz/Elektr) sarfi"),
        ('9220', instance.labor_cost, "Mehnat haqi xarajati"),
        ('9220', instance.overhead_cost, "Umumiy zavod xarajatlari"),
        ('9220', instance.cnc_cost, "CNC ishlov berish xarajati"),
    ]

    for code, amt, desc in other_costs:
        if amt > 0:
            lines.append({
                'account_code': code,
                'debit': 0,
                'credit': amt,
                'description': desc,
            })

    _safe_create_entry(
        description=f"Batch yopildi (Costing): {instance.batch_number} | Unit Cost: {instance.unit_cost:,.2f}",
        lines=lines,
        source_type='PRODUCTION',
        source_id=instance.id,
        source_description=f"ProductionBatch #{instance.batch_number}",
    )

