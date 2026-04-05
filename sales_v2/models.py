from django.db import models
from django.conf import settings

class Customer(models.Model):
    CUSTOMER_TYPE_CHOICES = (
        ('WHOLESALE', 'Ulgurji'),
        ('RETAIL', 'Chakana'),
    )
    LEAD_STATUS_CHOICES = (
        ('LEAD', 'Yangi Lead'),
        ('NEGOTIATION', 'Muzokara'),
        ('WON', 'Yutilgan'),
        ('LOST', 'Yutqazilgan'),
    )
    INTEREST_CHOICES = (
        ('HIGH', 'Yuqori'),
        ('MEDIUM', 'O\'rtacha'),
        ('LOW', 'Past'),
    )
    name = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50)
    secondary_phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True)
    stir_inn = models.CharField(max_length=20, blank=True, null=True, verbose_name="STIR / INN")
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPE_CHOICES, default='RETAIL')
    
    # CRM Fields
    lead_status = models.CharField(max_length=20, choices=LEAD_STATUS_CHOICES, default='LEAD')
    interest_level = models.CharField(max_length=10, choices=INTEREST_CHOICES, default='MEDIUM')
    assigned_manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_clients')
    
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name if self.company_name else self.name

class ContactLog(models.Model):
    CONTACT_TYPE_CHOICES = (
        ('CALL', 'Telefon qo\'ng\'irog\'i'),
        ('MEETING', 'Uchrashuv'),
        ('TELEGRAM', 'Telegram / Messencer'),
        ('EMAIL', 'Email'),
        ('OTHER', 'Boshqa'),
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='contact_logs')
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    contact_type = models.CharField(max_length=20, choices=CONTACT_TYPE_CHOICES, default='CALL')
    notes = models.TextField()
    follow_up_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.name} - {self.contact_type} - {self.created_at.date()}"

class Invoice(models.Model):
    STATUS_CHOICES = (
        ('NEW', 'Yangi'),
        ('CONFIRMED', 'Tasdiqlangan'),
        ('IN_PRODUCTION', 'Ishlab chiqarishda'),
        ('READY', 'Tayyor'),
        ('SHIPPED', 'Jo\'natilgan'),
        ('EN_ROUTE', 'Yo\'lda'),
        ('DELIVERED', 'Yetkazildi'),
        ('COMPLETED', 'Yakunlangan'),
        ('CANCELLED', 'Bekor qilingan'),
    )
    PAYMENT_CHOICES = (
        ('CASH', 'Naqd'),
        ('BANK', 'Bank (Perezichleniya)'),
        ('CARD', 'Karta'),
        ('DEBT', 'Qarz (Nasiya)'),
    )
    invoice_number = models.CharField(max_length=100, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoices')
    date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='CASH')
    delivery_address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # New Fields for LC and Business Rules
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    manager_limit_approval = models.BooleanField(default=False)
    production_order_id = models.IntegerField(null=True, blank=True, help_text="ID of the related production order if MTO")
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.invoice_number

class SaleItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('warehouse_v2.Material', on_delete=models.CASCADE)
    source_warehouse = models.ForeignKey('warehouse_v2.Warehouse', on_delete=models.SET_NULL, null=True, blank=True)
    batch_number = models.CharField(max_length=100, null=True, blank=True)
    quantity = models.FloatField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

class Delivery(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Kutilmoqda'),
        ('EN_ROUTE', 'Yo\'lda'),
        ('DELIVERED', 'Yetkazildi'),
        ('CANCELLED', 'Bekor qilindi'),
    )
    invoice = models.OneToOneField(Invoice, on_delete=models.CASCADE, related_name='delivery')
    courier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    started_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Delivery for {self.invoice.invoice_number}"


class Contract(models.Model):
    STATUS_CHOICES = (
        ('DRAFT', 'Qoralama'),
        ('ACTIVE', 'Aktiv'),
        ('EXPIRED', 'Muddati o\'tgan'),
        ('CANCELLED', 'Bekor qilingan'),
    )
    contract_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='contracts')
    title = models.CharField(max_length=255, default='Yetkazib berish shartnomasi')
    start_date = models.DateField()
    end_date = models.DateField()
    total_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    terms = models.TextField(blank=True, help_text="Shartnoma shartlari")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.contract_number:
            last = Contract.objects.order_by('-id').first()
            num = (last.id + 1) if last else 1
            self.contract_number = f"SHR-{num:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.contract_number} — {self.customer.name}"

    @property
    def days_remaining(self):
        from datetime import date
        delta = self.end_date - date.today()
        return max(delta.days, 0)


class NotificationLog(models.Model):
    EVENT_CHOICES = (
        ('NEW_ORDER', 'Yangi buyurtma'),
        ('PAYMENT_RECEIVED', 'To\'lov qabul qilindi'),
        ('ORDER_SHIPPED', 'Buyurtma jo\'natildi'),
        ('DEBT_REMINDER', 'Qarz eslatmasi'),
        ('CONTRACT_EXPIRY', 'Shartnoma muddati tugayapti'),
    )
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    message = models.TextField()
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    is_sent = models.BooleanField(default=False)
    sent_via = models.CharField(max_length=20, default='LOG', help_text="LOG or TELEGRAM")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type} — {self.created_at}"
