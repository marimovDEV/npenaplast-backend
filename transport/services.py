from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from rest_framework.exceptions import ValidationError
from .models import Waybill, Trip, DriverPayment, TransportContract
from finance.services import record_double_entry

def start_trip(waybill_id, user=None):
    """
    Transitions a Waybill to CONFIRMED and starts a Trip.
    """
    with transaction.atomic():
        waybill = Waybill.objects.select_for_update().get(id=waybill_id)
        if waybill.status != 'DRAFT':
            raise ValidationError(f"Waybillni boshlab bo'lmaydi. Joriy holat: {waybill.status}")
            
        waybill.status = 'CONFIRMED'
        waybill.dispatcher = user
        waybill.save()
        
        trip, created = Trip.objects.get_or_create(
            waybill=waybill,
            defaults={'status': 'EN_ROUTE', 'start_time': timezone.now()}
        )
        if not created:
            trip.status = 'EN_ROUTE'
            trip.start_time = timezone.now()
            trip.save()
            
        return trip

def complete_trip(trip_id, actual_distance, user=None):
    """
    Finalizes the trip, calculates payment, and records financial liability.
    """
    with transaction.atomic():
        trip = Trip.objects.select_for_update().get(id=trip_id)
        if trip.status == 'COMPLETED':
            return trip
            
        trip.status = 'COMPLETED'
        trip.end_time = timezone.now()
        trip.actual_distance = actual_distance
        trip.save()
        
        waybill = trip.waybill
        waybill.status = 'COMPLETED'
        waybill.save()
        
        # Calculate Payment based on Contract
        payment = calculate_driver_payment(trip)
        
        # Finance Integration: Transport Expense (9410) -> Driver Payable (6020)
        # We assume Account codes are seeded
        record_double_entry(
            description=f"Haydovchi xizmati: {waybill.driver.full_name} | {waybill.waybill_number}",
            entries=[
                {'account_code': '9410', 'debit': payment.amount, 'credit': 0}, # Expense
                {'account_code': '6020', 'debit': 0, 'credit': payment.amount}, # Payable
            ],
            reference=waybill.waybill_number,
            user=user
        )
        
        return trip

def calculate_driver_payment(trip):
    """
    Core business logic for calculating driver earnings based on contract type.
    """
    driver = trip.waybill.driver
    contract = TransportContract.objects.filter(driver=driver, status='ACTIVE').first()
    
    if not contract:
        raise ValidationError(f"Haydovchi {driver.full_name} bilan aktiv shartnoma topilmadi.")
        
    amount = Decimal('0')
    rate = Decimal('0')
    
    if contract.payment_type == 'PER_KM':
        rate = contract.price_per_km
        amount = Decimal(str(trip.actual_distance)) * rate
    else: # PER_TRIP
        rate = contract.price_per_trip
        amount = rate
        
    payment = DriverPayment.objects.create(
        driver=driver,
        trip=trip,
        calculated_km=trip.actual_distance,
        rate=rate,
        amount=amount,
        status='PENDING'
    )
    return payment
