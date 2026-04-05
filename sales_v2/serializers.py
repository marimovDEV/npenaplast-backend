from rest_framework import serializers
from .models import Customer, Invoice, SaleItem, ContactLog, Delivery, Contract, NotificationLog

class ContactLogSerializer(serializers.ModelSerializer):
    manager_name = serializers.ReadOnlyField(source='manager.username')
    
    class Meta:
        model = ContactLog
        fields = '__all__'

class CustomerSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    customer_type_display = serializers.CharField(source='get_customer_type_display', read_only=True)
    orders_count = serializers.SerializerMethodField()
    total_purchased = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'company_name', 'phone', 'secondary_phone', 
            'email', 'address', 'stir_inn', 'customer_type', 
            'customer_type_display', 'credit_limit', 'balance',
            'orders_count', 'total_purchased', 'lead_status',
            'interest_level', 'assigned_manager', 'created_at'
        ]
    
    def get_balance(self, obj):
        try:
            return float(obj.balance.total_debt)
        except:
            return 0.0

    def get_orders_count(self, obj):
        return obj.invoices.count()

    def get_total_purchased(self, obj):
        from django.db.models import Sum
        total = obj.invoices.aggregate(Sum('total_amount'))['total_amount__sum']
        return float(total) if total else 0.0

class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    source_warehouse_name = serializers.ReadOnlyField(source='source_warehouse.name')

    class Meta:
        model = SaleItem
        fields = '__all__'

class InvoiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.name')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    items = SaleItemSerializer(many=True, read_only=True)
    created_by_name = serializers.ReadOnlyField(source='created_by.username')

    class Meta:
        model = Invoice
        fields = '__all__'

class DeliverySerializer(serializers.ModelSerializer):
    courier_name = serializers.ReadOnlyField(source='courier.username')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    invoice_number = serializers.ReadOnlyField(source='invoice.invoice_number')
    customer_name = serializers.ReadOnlyField(source='invoice.customer.name')
    address = serializers.ReadOnlyField(source='invoice.delivery_address')

    class Meta:
        model = Delivery
        fields = '__all__'

class CourierAssignSerializer(serializers.Serializer):
    courier_id = serializers.IntegerField()


class ContractSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.name')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.ReadOnlyField(source='created_by.username')
    days_remaining = serializers.ReadOnlyField()

    class Meta:
        model = Contract
        fields = '__all__'
        read_only_fields = ['contract_number']

class NotificationLogSerializer(serializers.ModelSerializer):
    event_display = serializers.CharField(source='get_event_type_display', read_only=True)
    customer_name = serializers.ReadOnlyField(source='customer.name')

    class Meta:
        model = NotificationLog
        fields = '__all__'
