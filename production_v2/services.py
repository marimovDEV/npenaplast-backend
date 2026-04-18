from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from inventory.services import update_inventory
from transactions.services import create_transaction
from finance.services import record_double_entry
from common_v2.services import log_action
from warehouse_v2.models import RawMaterialBatch, Warehouse, Material
from .models import Zames, BlockProduction, DryingProcess, ProductionOrder, ProductionOrderStage, StageActionLog, Bunker


def _ensure_production_order_document(order, user=None):
    from documents.models import Document, DocumentItem

    document, _ = Document.objects.get_or_create(
        type='PRODUCTION_ORDER',
        number=order.order_number,
        defaults={
            'status': 'CREATED',
            'created_by': user or order.responsible,
        },
    )

    if order.product and not document.items.exists():
        DocumentItem.objects.create(
            document=document,
            product=order.product,
            quantity=order.quantity,
            price_at_moment=0,
            batch_number=f"PROD-{order.order_number}",
        )
    return document


def _create_stage_update_document(stage, action, user=None, notes=''):
    from documents.models import Document, DocumentItem

    sequence_number = stage.sequence + 1
    document = Document.objects.create(
        type='STAGE_UPDATE',
        number=f"{stage.order.order_number}-{stage.stage_type}-{sequence_number:02d}-{action}",
        status='DONE' if action in ['FINISH', 'FAIL', 'RESET'] else 'CREATED',
        created_by=user or stage.current_operator or stage.order.responsible,
    )

    if stage.order.product:
        DocumentItem.objects.create(
            document=document,
            product=stage.order.product,
            quantity=stage.actual_quantity or stage.order.quantity,
            price_at_moment=0,
            batch_number=notes[:100] or None,
        )
    return document


def _mark_linked_invoice_ready(order, warehouse=None):
    if not order.source_order or not order.source_order.startswith('ORD-'):
        return

    try:
        from sales_v2.models import Invoice

        invoice = Invoice.objects.filter(
            invoice_number=order.source_order,
            status='IN_PRODUCTION'
        ).first()
        if not invoice:
            return

        invoice.status = 'READY'
        invoice.save(update_fields=['status'])

        production_batch = f"PROD-{order.order_number}"
        source_warehouse = warehouse
        for item in invoice.items.filter(product=order.product):
            if not item.batch_number:
                item.batch_number = production_batch
            if not item.source_warehouse_id and source_warehouse:
                item.source_warehouse = source_warehouse
            item.save(update_fields=['batch_number', 'source_warehouse'])
    except Exception:
        pass

def complete_block_production(zames, form_number, block_count, length, width, height, density, user=None):
    """
    Records the physical production of blocks from a Zames.
    Initiates the DRYING status.
    """
    with transaction.atomic():
        # Calculate volume: (L * W * H / 10^9) * count
        volume = (length * width * height / 1e9) * block_count
        
        block_batch = BlockProduction.objects.create(
            zames=zames,
            form_number=form_number,
            block_count=block_count,
            length=length,
            width=width,
            height=height,
            density=density,
            volume=volume,
            status='DRYING'
        )
        
        # Start Drying Process
        DryingProcess.objects.create(block_production=block_batch)
        
        log_action(
            user=user,
            action='CREATE',
            module='Production',
            description=f"Bloklar quyildi: {block_count} dona ({density} kg/m3). Status: Quritilmoqda.",
            object_id=block_batch.id
        )
        return block_batch

def finish_drying_process(block_production_id, user=None):
    """
    Finalizes the drying phase and marks blocks as READY in Sklad 2.
    """
    with transaction.atomic():
        block_batch = BlockProduction.objects.get(id=block_production_id)
        if block_batch.status != 'DRYING':
            raise ValidationError(f"Blok quritish holatida emas. Joriy status: {block_batch.status}")

        drying = block_batch.drying_processes.filter(end_time__isnull=True).first()
        if drying:
            drying.end_time = timezone.now()
            drying.save()

        block_batch.status = 'READY'
        
        # Ensure it's assigned to Sklad 2
        sklad2 = Warehouse.objects.filter(name__icontains='Sklad №2').first()
        block_batch.warehouse = sklad2
        block_batch.save()

        # Record Inventory in Sklad 2
        # Use the first material from Zames items as the product reference
        zames_material = block_batch.zames.items.first()
        product_ref = zames_material.material if zames_material else None
        
        if product_ref:
            create_transaction(
                product=product_ref,
                from_wh=None,
                to_wh=sklad2,
                qty=block_batch.block_count,
                trans_type='PRODUCTION',
                batch_number=block_batch.form_number
            )
            
            # Finance: WIP (Blocks) -> WIP (Expanded)
            # For now, we use a simplified cost estimate or 0-value move if cost is not yet tracked per item
            record_double_entry(
                description=f"Blok ishlab chiqarildi: {block_batch.form_number}",
                entries=[
                    {'account_code': '2020', 'debit': Decimal('0'), 'credit': Decimal('0')}, # WIP Move
                ],
                reference=f"BLOCK-{block_batch.id}",
                user=user
            )

        log_action(
            user=user,
            action='UPDATE',
            module='Production',
            description=f"Bloklar quritildi va Sklad 2 ga o'tkazildi: {block_batch}",
            object_id=block_batch.id
        )
        return block_batch
def start_zames(zames, user=None):
    """
    Transitions a Zames to IN_PROGRESS.
    Checks stock availability in Sklad 1 before starting.
    """
    if zames.status != 'PENDING':
        raise ValidationError(f"Zamesni boshlab bo'lmaydi. Joriy status: {zames.status}")
    
    # Validation: Check Sklad 1 stock
    sklad1 = Warehouse.objects.filter(name__icontains='Sklad №1').first()
    if not sklad1:
        sklad1 = Warehouse.objects.first()

    for item in zames.items.all():
        from warehouse_v2.models import Stock
        stock = Stock.objects.filter(warehouse=sklad1, material=item.material).first()
        if not stock or stock.quantity < item.quantity:
            raise ValidationError(f"Xom-ashyo yetarli emas: {item.material.name}. Omborda: {stock.quantity if stock else 0} {item.material.unit}")

    zames.status = 'IN_PROGRESS'
    zames.start_time = timezone.now()
    zames.save()
    
    log_action(
        user=user or zames.operator,
        action='UPDATE',
        module='Production',
        description=f"Zames boshlandi: {zames.zames_number}",
        object_id=zames.id
    )
    return zames

def finish_zames(zames, output_weight, user=None):
    """
    Finalizes a Zames, deducts inventory from Sklad 1, 
    calculates real-time costs, and adds semi-finished product to Sklad 2.
    """
    if zames.status != 'IN_PROGRESS':
        raise ValidationError(f"Zamesni yakunlab bo'lmaydi. Jarayonda emas.")
    
    from accounting.services import create_journal_entry
    
    with transaction.atomic():
        total_mix_cost = Decimal('0')
        accounting_lines = []

        # 1. Deduct Input Materials (Sklad 1) & Calculate Costs
        sklad1 = Warehouse.objects.filter(name__icontains='Sklad №1').first()
        if not sklad1:
             sklad1 = Warehouse.objects.first()

        for item in zames.items.all():
            # Get cost at this moment
            price_per_unit = Decimal('0')
            if item.batch and item.batch.price_per_unit:
                price_per_unit = item.batch.price_per_unit
            else:
                price_per_unit = item.material.price
            
            item.unit_cost = price_per_unit
            item.total_cost = Decimal(str(item.quantity)) * price_per_unit
            item.save()
            
            total_mix_cost += item.total_cost

            # Stock Deduction
            create_transaction(
                product=item.material,
                from_wh=sklad1,
                to_wh=None, # Consumed
                qty=item.quantity,
                trans_type='PRODUCTION',
                batch_number=item.batch.batch_number if item.batch else None
            )

            # Accounting Credit Line (Account 1010 - Raw Materials)
            accounting_lines.append({
                'account_code': '1010',
                'debit': 0,
                'credit': item.total_cost,
                'description': f"Xom-ashyo sarfi: {item.material.name} ({zames.zames_number})"
            })

        # 2. Update Zames details
        zames.status = 'DONE'
        zames.end_time = timezone.now()
        zames.output_weight = output_weight
        zames.input_weight = sum(item.quantity for item in zames.items.all())
        zames.save()
        
        # 3. Create Expanded Material Batch (Sklad 2)
        sklad2 = Warehouse.objects.filter(name__icontains='Sklad №2').first()
        expanded_material = Material.objects.filter(name__icontains='Granula EPS').first() 
        batch_no = f"EXP-{zames.zames_number}"
        
        RawMaterialBatch.objects.create(
            invoice_number=f"PROD-{zames.zames_number}",
            material=expanded_material,
            quantity_kg=output_weight,
            batch_number=batch_no,
            status='IN_STOCK',
            price_per_unit = total_mix_cost / Decimal(str(output_weight)) if output_weight > 0 else 0,
            responsible_user=user or zames.operator,
            date=timezone.now().date()
        )
        
        create_transaction(
            product=expanded_material,
            from_wh=None,
            to_wh=sklad2,
            qty=output_weight,
            trans_type='PRODUCTION',
            batch_number=batch_no
        )

        # 4. Accounting Entry: Debit WIP (Account 2010), Credit Materials (1010)
        # Note: We already have credit lines, now add the total debit line
        accounting_lines.append({
          'account_code': '2010',
          'debit': total_mix_cost,
          'credit': 0,
          'description': f"Ishlab chiqarish xarajatlari (Mixing): {zames.zames_number}"
        })

        if total_mix_cost > 0:
            create_journal_entry(
                description=f"Zames tannarxi qayd etildi: {zames.zames_number}",
                lines=accounting_lines,
                source_type='PRODUCTION',
                source_id=zames.id,
                user=user or zames.operator,
                auto_post=True
            )

        log_action(
            user=user or zames.operator,
            action='UPDATE',
            module='Production',
            description=f"Zames yakunlandi: {zames.zames_number}. Umumiy tannarx: {total_mix_cost} UZS",
            object_id=zames.id
        )
        
def assign_task_to_operator(stage_id, operator_id, user=None):
    """
    Explicitly assigns a stage to an operator and moves it to ACTIVE.
    """
    with transaction.atomic():
        stage = ProductionOrderStage.objects.get(id=stage_id)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        operator = User.objects.get(id=operator_id)
        
        stage.current_operator = operator
        stage.status = 'ACTIVE'
        stage.started_at = timezone.now()
        stage.save()
        
        log_action(
            user=user,
            action='UPDATE',
            module='Production',
            description=f"Topshiriq biriktirildi: {stage.stage_type} -> {operator.username}",
            object_id=stage.id
        )
        return stage

def calculate_plan_material_needs(plan_id):
    """
    Estimates raw materials needed for all orders in a plan.
    """
    from .models import ProductionPlan, RecipeItem
    plan = ProductionPlan.objects.get(id=plan_id)
    needs = {}
    
    for order in plan.orders.all():
        # Find recipe for the product
        recipe = order.product.recipes.first() if hasattr(order.product, 'recipes') else None
        if not recipe: continue
        
        for item in recipe.items.all():
            mat_id = item.material.id
            qty = item.quantity * order.quantity
            needs[mat_id] = needs.get(mat_id, 0) + qty
            
    return needs

def start_plan(plan_id, user=None):
    plan = ProductionPlan.objects.get(id=plan_id)
    plan.status = 'ACTIVE'
    plan.start_time = timezone.now()
    plan.save()
    return plan

def complete_plan(plan_id, actual_volume, user=None):
    plan = ProductionPlan.objects.get(id=plan_id)
    plan.status = 'COMPLETED'
    plan.end_time = timezone.now()
    plan.actual_volume = actual_volume
    plan.save()
    return plan

def create_production_order(product, quantity, order_number=None, deadline=None, user=None, source="STOCK", priority='MEDIUM'):
    """
    Creates a new ProductionOrder and initializes its pipeline stages.
    """
    if not order_number:
        order_number = f"PN-{timezone.now().strftime('%y%m%d%H%M%S')}"

    with transaction.atomic():
        order = ProductionOrder.objects.create(
            order_number=order_number,
            product=product,
            quantity=quantity,
            deadline=deadline,
            responsible=user,
            source_order=source,
            priority=priority
        )

        # Initialize stages in standard sequence
        stages = [
            ('ZAMES', 'Zames (Mixing)'),
            ('DRYING', 'Quritish'),
            ('BUNKER', 'Bunker (Resting)'),
            ('FORMOVKA', 'Formovka (Molding)'),
            ('BLOK', 'Blok (Cutting/Sizing)'),
            ('CNC', 'CNC (Cutting)'),
            ('DEKOR', 'Dekor (Finishing)'),
        ]

        for i, (stage_code, _) in enumerate(stages):
            ProductionOrderStage.objects.create(
                order=order,
                stage_type=stage_code,
                sequence=i,
                status='PENDING',
                started_at=None
            )
        
        order.status = 'IN_PROGRESS'
        order.save()
        _ensure_production_order_document(order, user=user)
        
        log_action(
            user=user,
            action='CREATE',
            module='Production',
            description=f"Yangi Buyurtma-Naryad yaratildi: {order_number}",
            object_id=order.id
        )
        return order

def transition_to_next_stage(stage_id, user=None, related_id=None):
    """
    Completes the current stage and activates the next one in the sequence.
    """
    with transaction.atomic():
        # Find and complete the current stage
        current_stage = ProductionOrderStage.objects.select_for_update().select_related('order').get(id=stage_id)
        if current_stage.status == 'DONE':
            return current_stage.order # Idempotent

        order = current_stage.order

        # Complete current stage
        current_stage.status = 'DONE'
        current_stage.completed_at = timezone.now()
        if related_id:
            current_stage.related_id = related_id
        current_stage.save()

        # Release Bunker if this was a Bunker stage
        if current_stage.stage_type == 'BUNKER' and current_stage.related_id:
            try:
                # Find the bunker linked to this stage
                from .models import BunkerLoad
                load = BunkerLoad.objects.filter(id=current_stage.related_id).first()
                if load:
                    load.bunker.is_occupied = False
                    load.bunker.save()
                    log_action(user=user, action='UPDATE', module='Production', description=f"Bunker bo'shatildi: {load.bunker.name}", object_id=load.bunker.id)
            except Exception:
                pass

        # Log completion
        StageActionLog.objects.create(
            order=order,
            stage=current_stage,
            stage_type=current_stage.stage_type,
            action='FINISH',
            user=user
        )
        _create_stage_update_document(current_stage, 'FINISH', user=user)

        # Find the next stage and set it to PENDING
        next_stage = order.stages.filter(sequence=current_stage.sequence + 1).first()
        if next_stage:
            next_stage.status = 'PENDING'
            next_stage.save()
        else:
            # All stages completed
            order.status = 'COMPLETED'
            order.progress = 100.0
            order.save()
            
            # --- MES Stock Update: Add finished product to Warehouse ---
            sklad4 = None
            try:
                from warehouse_v2.models import Warehouse
                from inventory.services import update_inventory
                
                # Sklad 4 is the default for finished goods. Try multiple lookups for robustness.
                sklad4 = Warehouse.objects.filter(name__icontains='Sklad №4').first() or \
                         Warehouse.objects.filter(name__icontains='4').filter(name__icontains='Sklad').first()
                         
                if sklad4 and order.product:
                    update_inventory(
                        product=order.product,
                        warehouse=sklad4,
                        qty=order.quantity,
                        batch_number=f"PROD-{order.order_number}"
                    )
                    # Use print for immediate visibility in simulation logs
                    print(f"DEBUG: Stock added to {sklad4.name} for {order.product.name} ({order.quantity} units)")
                else:
                    print(f"DEBUG: Stock NOT added. Sklad4 found: {sklad4.name if sklad4 else 'None'}, Product: {order.product}")
            except Exception as e:
                print(f"DEBUG: Error updating finished goods stock: {e}")

            _mark_linked_invoice_ready(order, warehouse=sklad4)

        # Update overall order progress
        total_stages = order.stages.count()
        completed_stages = order.stages.filter(status='DONE').count()
        if total_stages > 0:
            order.progress = (completed_stages / total_stages) * 100
            order.save()

        log_action(
            user=user,
            action='UPDATE',
            module='Production',
            description=f"Bosqich o'zgartirildi: {current_stage.stage_type} -> {next_stage.stage_type if next_stage else 'FINISH'}",
            object_id=order.id
        )
        return order

def perform_quality_check(order_id, status, notes='', waste_weight=0, inspector=None):
    """
    Performs a quality check on a production order.
    PASSED -> Moves to READY/SHIPPED if applicable.
    FAILED -> Moves to REPAIR and creates a WasteTask.
    """
    from .models import QualityCheck, ProductionOrder
    from waste_v2.services import create_waste_task

    with transaction.atomic():
        order = ProductionOrder.objects.get(id=order_id)
        
        qc = QualityCheck.objects.create(
            order=order,
            status=status,
            notes=notes,
            waste_weight=waste_weight,
            inspector=inspector
        )
        
        if status == 'PASSED':
            order.status = 'COMPLETED'
            order.progress = 100.0
            sklad4 = Warehouse.objects.filter(name__icontains='Sklad №4').first() or \
                     Warehouse.objects.filter(name__icontains='4').filter(name__icontains='Sklad').first()
            _mark_linked_invoice_ready(order, warehouse=sklad4)
        else:
            order.status = 'REPAIR'
            # Create a waste task for the rejected material
            if waste_weight > 0:
                create_waste_task(
                    source=f"QC Reject: {order.order_number}",
                    material=order.product,
                    weight=waste_weight,
                    user=inspector
                )
        
        order.save()
        
        log_action(
            user=inspector,
            action='QC',
            module='Production',
            description=f"Sifat nazorati: {order.order_number} -> {status}. {notes}",
            object_id=qc.id
        )
        return qc

def start_production_stage(stage_id, user=None, extra_data=None):
    """
    Manually starts a production stage (PENDING -> ACTIVE) with strict validation.
    """
    with transaction.atomic():
        # Lock the stage to prevent double-processing
        stage = ProductionOrderStage.objects.select_for_update().select_related('order').get(id=stage_id)
        
        if stage.status == 'ACTIVE':
            return stage # Idempotent
        
        if stage.status != 'PENDING' and stage.status != 'PAUSED':
            raise ValidationError(f"Bosqichni boshlab bo'lmaydi. Joriy holat: {stage.status}")
            
        # WIP Limit for ZAMES
        if stage.stage_type == 'ZAMES':
            active_zames_count = ProductionOrderStage.objects.filter(stage_type='ZAMES', status='ACTIVE').count()
            if active_zames_count >= 2:
                raise ValidationError("WIP Limit: Hozirda 2 ta aktiv Zames mavjud. Navbat kuting.")

        # Sequence Validation: check if previous stage is DONE
        if stage.sequence > 0:
            prev_stage = stage.order.stages.filter(sequence=stage.sequence - 1).first()
            if prev_stage and prev_stage.status != 'DONE':
                raise ValidationError(f"Oldingi bosqich ({prev_stage.get_stage_type_display()}) hali yakunlanmagan.")

        # Resource Allocation: Bunker specific logic
        if stage.stage_type == 'BUNKER':
            bunker_id = extra_data.get('bunker_id') if extra_data else None
            if not bunker_id:
                raise ValidationError("Bunker tanlanmagan.")
            
            bunker = Bunker.objects.select_for_update().get(id=bunker_id)
            if bunker.is_occupied:
                raise ValidationError(f"Bunker №{bunker.name} band. Boshqa bunker tanlang.")
            
            # Identify the Zames to load
            zames_id = extra_data.get('zames_id')
            if not zames_id: # Try to find zames from previous stage
                zames_stage = stage.order.stages.filter(stage_type='ZAMES').first()
                zames_id = zames_stage.related_id if zames_stage else None
            
            if not zames_id:
                raise ValidationError("Yuklanadigan Zames topilmadi.")

            from .models import BunkerLoad, Zames
            load = BunkerLoad.objects.create(
                zames_id=zames_id,
                bunker=bunker,
                required_time=extra_data.get('required_time', 120)
            )
            bunker.is_occupied = True
            bunker.last_occupied_at = timezone.now()
            bunker.save()
            
            stage.related_id = load.id # Link load for later release

        action = 'RESUME' if stage.status == 'PAUSED' else 'START'
        stage.status = 'ACTIVE'
        stage.started_at = stage.started_at or timezone.now()
        stage.current_operator = user
        stage.save()
        
        # Log action
        StageActionLog.objects.create(
            order=stage.order,
            stage=stage,
            stage_type=stage.stage_type,
            action=action,
            user=user
        )
        _create_stage_update_document(stage, action, user=user)

        log_action(
            user=user,
            action='UPDATE',
            module='Production',
            description=f"Bosqich boshlandi: {stage.order.order_number} - {stage.stage_type}",
            object_id=stage.id
        )
        return stage

def fail_production_stage(stage_id, reason, user=None):
    """
    Marks a stage as FAILED with a reason.
    """
    with transaction.atomic():
        stage = ProductionOrderStage.objects.select_for_update().get(id=stage_id)
        stage.status = 'FAILED'
        stage.save()
        
        StageActionLog.objects.create(
            order=stage.order,
            stage=stage,
            stage_type=stage.stage_type,
            action='FAIL',
            user=user,
            notes=reason
        )
        _create_stage_update_document(stage, 'FAIL', user=user, notes=reason)
        
        log_action(
            user=user,
            action='UPDATE',
            module='Production',
            description=f"Bosqich to'xtatildi (FAILED): {stage.order.order_number} - {reason}",
            object_id=stage.id
        )
        return stage

def force_release_bunker(bunker_id, user=None):
    """
    Admin override to free a bunker.
    """
    with transaction.atomic():
        bunker = Bunker.objects.select_for_update().get(id=bunker_id)
        bunker.is_occupied = False
        bunker.save()
        
        log_action(
            user=user,
            action='UPDATE',
            module='Production',
            description=f"Bunker majburiy bo'shatildi (Admin): {bunker.name}",
            object_id=bunker.id
        )
        return bunker

def force_complete_stage(stage_id, user=None, reason="Admin override"):
    """
    Emergency override to finish a stage regardless of inputs.
    """
    with transaction.atomic():
        stage = ProductionOrderStage.objects.select_for_update().get(id=stage_id)
        if stage.status == 'DONE':
            return stage.order

        StageActionLog.objects.create(
            order=stage.order,
            stage=stage,
            stage_type=stage.stage_type,
            action='FINISH',
            user=user,
            notes=f"FORCE COMPLETE: {reason}"
        )
        _create_stage_update_document(stage, 'FINISH', user=user, notes=f"FORCE COMPLETE: {reason}")

        log_action(
            user=user,
            action='UPDATE',
            module='Production',
            description=f"Bosqich majburiy yakunlandi: {stage.order.order_number} - {stage.stage_type}. Sabab: {reason}",
            object_id=stage.id
        )

        # Let the standard transition logic mark this stage as DONE and advance the pipeline.
        return transition_to_next_stage(stage.id, user=user)

def reset_stage_to_pending(stage_id, user=None, reason="Admin reset"):
    """
    Resets an ACTIVE or FAILED stage back to PENDING.
    Used for accidental starts.
    """
    with transaction.atomic():
        stage = ProductionOrderStage.objects.select_for_update().get(id=stage_id)
        old_status = stage.status
        stage.status = 'PENDING'
        stage.started_at = None
        stage.current_operator = None
        stage.save()
        
        StageActionLog.objects.create(
            order=stage.order,
            stage=stage,
            stage_type=stage.stage_type,
            action='RESET',
            user=user,
            notes=f"RESET FROM {old_status}: {reason}"
        )
        _create_stage_update_document(stage, 'RESET', user=user, notes=f"RESET FROM {old_status}: {reason}")
        
        log_action(
            user=user,
            action='UPDATE',
            module='Production',
            description=f"Bosqich qayta tiklandi (RESET): {stage.order.order_number} - {stage.stage_type}",
            object_id=stage.id
        )
        return stage

from decimal import Decimal
from .models import ProductionBatch

class CostCalculationService:
    @staticmethod
    def calculate_batch_cost(batch: ProductionBatch, auto_distribute=True):
        """
        Calculates and sums all cost components for a batch.
        Runs when the batch goes from OPEN to CLOSED.
        """
        # 1. Material Cost
        material_cost = Decimal(0)
        for z in batch.zames_list.all():
            for item in z.items.all():
                if item.batch and item.batch.price_per_unit:
                    material_cost += Decimal(str(item.quantity)) * item.batch.price_per_unit
                elif item.material and item.material.price:
                    material_cost += Decimal(str(item.quantity)) * item.material.price
        
        # 2. Energy
        energy_cost = Decimal(0)
        for eu in batch.energy_usages.all():
            energy_cost += eu.total_cost

        if auto_distribute and energy_cost == 0:
            # Hybrid fallback: If no explicit energy was placed, distribute generic.
            avg_zames = batch.zames_list.count()
            fallback_gas = Decimal(12 * avg_zames) * Decimal('1500.00')
            fallback_elec = Decimal(45 * avg_zames) * Decimal('450.00')
            energy_cost = fallback_gas + fallback_elec
            batch.cost_confidence = 'ESTIMATED'
        else:
            batch.cost_confidence = 'REAL' if energy_cost > 0 else 'ESTIMATED'

        # 3. Labor
        labor_cost = Decimal(0)
        for lc in batch.labor_costs.all():
            labor_cost += lc.total_cost

        # 4. Overhead
        overhead_cost = Decimal(0)
        for oc in batch.overhead_costs.all():
            overhead_cost += oc.amount

        # 5. CNC
        cnc_cost = Decimal(0)
        for job in batch.cnc_jobs.all():
            # Estimate CNC cost based on duration or waste if needed
            # For now, placeholder or link to specific energy usage
            pass

        total = material_cost + energy_cost + labor_cost + overhead_cost + cnc_cost
        
        # Calculate unit cost
        total_blocks = batch.total_output_qty
        if total_blocks <= 0:
            total_blocks = 0
            for bp in batch.blocks.all():
                total_blocks += bp.block_count
            batch.total_output_qty = total_blocks

        unit_cost = total / Decimal(str(total_blocks)) if total_blocks > 0 else total

        # Update batch
        batch.material_cost = material_cost
        batch.energy_cost = energy_cost
        batch.labor_cost = labor_cost
        batch.overhead_cost = overhead_cost
        batch.cnc_cost = cnc_cost
        batch.total_cost = total
        batch.unit_cost = unit_cost
        
        batch.status = 'CLOSED'
        batch.end_time = timezone.now()
        batch.save()
        return batch

