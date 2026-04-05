from django.db import transaction
from django.utils import timezone
from .models import Delivery, DeliveryItem
from inventory.services import update_inventory

def create_delivery(type, destination_client=None, destination_project=None, driver_name='', vehicle_number='', invoice=None, trip=None, notes=''):
    return Delivery.objects.create(
        type=type,
        destination_client=destination_client,
        destination_project=destination_project,
        driver_name=driver_name,
        vehicle_number=vehicle_number,
        invoice=invoice,
        trip=trip,
        notes=notes
    )

def add_delivery_item(delivery_id, product, quantity, batch=None):
    delivery = Delivery.objects.get(id=delivery_id)
    return DeliveryItem.objects.create(
        delivery=delivery,
        product=product,
        quantity=quantity,
        batch=batch
    )

def start_shipment(delivery_id, user=None):
    with transaction.atomic():
        delivery = Delivery.objects.get(id=delivery_id)
        if delivery.status != 'PENDING':
            return delivery
        
        delivery.status = 'SENT'
        delivery.sent_at = timezone.now()
        delivery.save()
        
        # If it's a project supply, we handle the physical deduction here or in project services.
        # Usually, start_shipment for project supply should come from an internal warehouse.
        
        return delivery

def complete_delivery(delivery_id, user=None):
    with transaction.atomic():
        delivery = Delivery.objects.get(id=delivery_id)
        if delivery.status != 'SENT':
            return delivery
            
        delivery.status = 'DELIVERED'
        delivery.delivered_at = timezone.now()
        delivery.save()
        
        # If it's a sales delivery, it marks the invoice as DELIVERED if linked.
        if delivery.invoice:
            from sales_v2.services import transition_invoice_status
            transition_invoice_status(delivery.invoice_id, 'DELIVERED', performed_by=user)
            
        return delivery
