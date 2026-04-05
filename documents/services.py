from django.db import transaction
from rest_framework.exceptions import ValidationError
from transactions.services import create_transaction
from common_v2.services import log_action
from warehouse_v2.models import RawMaterialBatch, Supplier
from warehouse_v2.services import reserve_material_fifo, fulfill_reservation, release_reservation

def start_transfer_inventory(document, user=None):
    """
    Deducts stock from source warehouse and marks status as IN_TRANSIT.
    """
    with transaction.atomic():
        if document.status != 'CREATED':
            return document
            
        if not document.from_warehouse:
            raise ValidationError("O'tkazma uchun manba ombori kerak.")
            
        for item in document.items.all():
            create_transaction(
                product=item.product,
                from_wh=document.from_warehouse,
                to_wh=None, # Leave source, but not yet in destination
                qty=item.quantity,
                trans_type='TRANSFER',
                batch_number=item.batch_number
            )
        
        document.status = 'IN_TRANSIT'
        document.save()
        
        log_action(
            user=user or document.created_by,
            action='STATUS_CHANGE',
            module='Documents',
            description=f"Transfer yo'lga chiqdi: {document.number or document.qr_code}",
            object_id=document.id
        )
    return document

def finish_transfer_inventory(document, user=None):
    """
    Adds stock to destination warehouse and marks status as DONE.
    """
    with transaction.atomic():
        if document.status != 'IN_TRANSIT':
            raise ValidationError("Hujjat yo'lda emas, qabul qilib bo'lmaydi.")
            
        if not document.to_warehouse:
            raise ValidationError("O'tkazma uchun manzil ombori kerak.")
            
        for item in document.items.all():
            create_transaction(
                product=item.product,
                from_wh=None, # Already deducted from source
                to_wh=document.to_warehouse,
                qty=item.quantity,
                trans_type='TRANSFER',
                batch_number=item.batch_number
            )
            
        document.status = 'DONE'
        document.save()
        
        log_action(
            user=user or document.created_by,
            action='STATUS_CHANGE',
            module='Documents',
            description=f"Transfer qabul qilindi: {document.number or document.qr_code}",
            object_id=document.id
        )
    return document

def confirm_document(document, user=None):
    """
    Moves document from CREATED to CONFIRMED.
    For Outgoing documents, it reserves the necessary inventory.
    """
    with transaction.atomic():
        if document.status != 'CREATED':
            return document

        # Specific Logic for outgoing inventory
        if document.type in ['HISOB_FAKTURA_CHIQIM', 'OTKAZMA_BUYRUGI', 'ICHKI_YUK_XATI']:
            if document.from_warehouse and document.from_warehouse.name.startswith('Sklad №1'):
                for item in document.items.all():
                    reserve_material_fifo(item.product, item.quantity, document)

        document.status = 'CONFIRMED'
        document.save()
        
        log_action(
            user=user or document.created_by,
            action='STATUS_CHANGE',
            module='Documents',
            description=f"Hujjat tasdiqlandi: {document.number} ({document.type})",
            object_id=document.id
        )
    return document

def cancel_document(document, user=None):
    """
    Cancels a document. Releases any inventory reservations.
    """
    with transaction.atomic():
        if document.status in ['DONE', 'CANCELLED']:
            return document

        # Release any reservations
        release_reservation(document)

        document.status = 'CANCELLED'
        document.save()
        
        log_action(
            user=user or document.created_by,
            action='STATUS_CHANGE',
            module='Documents',
            description=f"Hujjat bekor qilindi: {document.number}",
            object_id=document.id
        )
    return document

def complete_document(document, user=None):
    """
    Marks a document as DONE and handles specific inventory logic based on document type.
    For Transfers, this is the final 'Receive' action.
    """
    with transaction.atomic():
        if document.status == 'DONE':
            return document

        # Categorical Logic
        if document.type == 'HISOB_FAKTURA_KIRIM':
            # Increase stock in destination warehouse
            for item in document.items.all():
                # Create a Batch record for Sklad 1
                batch_no = f"B-{document.number or document.id}-{item.id}"
                
                # Use standard supplier nomenclature if possible
                supplier_obj = document.supplier
                if not supplier_obj and document.supplier_name:
                    supplier_obj, _ = Supplier.objects.get_or_create(name=document.supplier_name)

                RawMaterialBatch.objects.create(
                    invoice_number=document.number or str(document.id),
                    supplier=supplier_obj,
                    quantity_kg=item.quantity,
                    remaining_quantity=item.quantity, # Initial tracking for FIFO
                    batch_number=batch_no,
                    price_per_unit=item.price_at_moment,
                    currency=document.currency,
                    responsible_user=user or document.created_by,
                    material_id=item.product_id,
                    status='IN_STOCK'
                )

                create_transaction(
                    product=item.product,
                    from_wh=None,
                    to_wh=document.to_warehouse,
                    qty=item.quantity,
                    trans_type='IN',
                    batch_number=batch_no
                )

        elif document.type == 'HISOB_FAKTURA_CHIQIM':
            # Decrease stock from source warehouse
            if not document.from_warehouse:
                raise ValidationError("Chiqim hujjati uchun ombor ko'rsatilmadi.")
            
            for item in document.items.all():
                create_transaction(
                    product=item.product,
                    from_wh=document.from_warehouse,
                    to_wh=None,
                    qty=item.quantity,
                    trans_type='SALE',
                    batch_number=item.batch_number,
                    document=document,
                    user=user or document.created_by
                )

        elif document.type in ['OTKAZMA_BUYRUGI', 'ICHKI_YUK_XATI']:
            # If it's a transfer FROM Sklad 1 (Raw Material), use the reservation logic
            if document.from_warehouse and document.from_warehouse.name.startswith('Sklad №1'):
                # Convert reservations to physical deductions
                fulfill_reservation(document, document.from_warehouse, user=user or document.created_by)
                
                # Update destination if also a warehouse
                if document.to_warehouse:
                    for item in document.items.all():
                        create_transaction(
                            product=item.product,
                            from_wh=None,
                            to_wh=document.to_warehouse,
                            qty=item.quantity,
                            trans_type='IN',
                            batch_number=f"TRF-{document.id}-{item.id}",
                            document=document,
                            user=user or document.created_by
                        )
            else:
                # Default behavior for other warehouses
                for item in document.items.all():
                    create_transaction(
                        product=item.product,
                        from_wh=document.from_warehouse,
                        to_wh=document.to_warehouse,
                        qty=item.quantity,
                        trans_type='TRANSFER',
                        batch_number=item.batch_number,
                        document=document,
                        user=user or document.created_by
                    )

        # Handle Production Logs (simplified)
        elif document.type in ['ZAMES_LOG', 'BUNKER_ENTRY', 'FORMOVKA_LOG']:
            for item in document.items.all():
                create_transaction(
                    product=item.product,
                    from_wh=document.from_warehouse,
                    to_wh=document.to_warehouse,
                    qty=item.quantity,
                    trans_type='PRODUCTION'
                )

        document.status = 'DONE'
        document.save()

        log_action(
            user=user or document.created_by,
            action='STATUS_CHANGE',
            module='Documents',
            description=f"Hujjat yakunlandi: {document.number or document.qr_code} ({document.type})",
            object_id=document.id
        )
        
        return document

def assign_courier(document, courier_user):
    """
    Assigns a courier to a document. Creates or updates DocumentDelivery.
    """
    from .models import DocumentDelivery
    with transaction.atomic():
        delivery, created = DocumentDelivery.objects.get_or_create(document=document)
        delivery.courier = courier_user
        delivery.save()
        
        # Optionally move status to SHIPPED if it was CONFIRMED
        if document.status == 'CONFIRMED':
            document.status = 'IN_TRANSIT'
            document.save()
            
    return delivery

def start_delivery(document, user=None):
    """
    Marks the start of the physical delivery (Pickup).
    """
    from django.utils import timezone
    try:
        delivery = document.delivery
    except document._meta.model.delivery.RelatedObjectDoesNotExist:
        raise ValidationError("Hujjatga hali kurer biriktirilmagan.")
        
    delivery.pickup_at = timezone.now()
    delivery.save()
    
    document.status = 'IN_TRANSIT'
    document.save()
    return delivery

def confirm_delivery(document, user=None):
    """
    Marks the delivery as completed (Recipient received).
    """
    from django.utils import timezone
    with transaction.atomic():
        try:
            delivery = document.delivery
        except document._meta.model.delivery.RelatedObjectDoesNotExist:
            raise ValidationError("Hujjatga hali kurer biriktirilmagan.")
            
        delivery.delivered_at = timezone.now()
        delivery.save()
        
        # Complete the document logic
        complete_document(document, user=user)
        
    return delivery

def update_document(document, data, user=None):
    """
    Updates document fields and items. ONLY allowed in CREATED (Draft) status.
    """
    with transaction.atomic():
        if document.status != 'CREATED':
            raise ValidationError("Faqat 'Yaratildi' (Draft) holatidagi hujjatlarni tahrirlash mumkin.")

        # Update basic fields
        if 'supplier_name' in data: document.supplier_name = data['supplier_name']
        if 'total_amount' in data: document.total_amount = data['total_amount']
        if 'currency' in data: document.currency = data['currency']
        if 'deadline' in data: document.deadline = data['deadline']
        
        # Handle Items if provided
        if 'items' in data:
            # Simple approach: clear and recreate for small doc items
            document.items.all().delete()
            from .models import DocumentItem
            for item_data in data['items']:
                DocumentItem.objects.create(
                    document=document,
                    product_id=item_data['product'],
                    quantity=item_data['quantity'],
                    price_at_moment=item_data.get('price_at_moment', 0),
                    batch_number=item_data.get('batch_number')
                )
        
        document.save()
        
        log_action(
            user=user or document.created_by,
            action='UPDATE',
            module='Documents',
            description=f"Hujjat tahrirlandi: {document.number}",
            object_id=document.id
        )
    return document
