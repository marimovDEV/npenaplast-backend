import csv
import io
import textwrap
from decimal import Decimal

from django.core.files.base import ContentFile
from django.db.models import Count, Sum
from django.utils import timezone

from cnc_v2.models import WasteProcessing
from production_v2.models import BlockProduction, Zames
from sales_v2.models import Invoice
from warehouse_v2.models import RawMaterialBatch, Stock


def _parse_period(period: str):
    today = timezone.now().date()
    if period == 'Today':
        return today, today
    if period == 'Last 7 Days':
        return today - timezone.timedelta(days=6), today
    if period == 'This Month':
        start = today.replace(day=1)
        return start, today
    return today - timezone.timedelta(days=29), today


def _build_rows(report_type: str, start_date, end_date):
    if report_type == 'SALES':
        invoices = Invoice.objects.filter(date__date__gte=start_date, date__date__lte=end_date).select_related('customer')
        rows = [[
            'Invoys', 'Sana', 'Mijoz', 'Status', 'Tolov', 'Summa'
        ]]
        total = Decimal('0')
        for inv in invoices:
            total += inv.total_amount
            rows.append([
                inv.invoice_number,
                inv.date.strftime('%Y-%m-%d'),
                inv.customer.name,
                inv.status,
                inv.payment_method,
                f'{inv.total_amount}',
            ])
        rows.append([])
        rows.append(['Jami', '', '', '', '', f'{total}'])
        return rows

    if report_type == 'INVENTORY':
        stocks = Stock.objects.select_related('warehouse', 'material').order_by('warehouse__name', 'material__name')
        rows = [['Ombor', 'Material', 'Qoldiq', 'Birlik', 'Qiymat']]
        total_value = Decimal('0')
        for stock in stocks:
            price = stock.material.price or Decimal('0')
            value = Decimal(str(stock.quantity)) * price
            total_value += value
            rows.append([
                stock.warehouse.name,
                stock.material.name,
                stock.quantity,
                stock.material.unit,
                f'{value}',
            ])
        rows.append([])
        rows.append(['Jami qiymat', '', '', '', f'{total_value}'])
        return rows

    if report_type == 'PRODUCTION':
        zames = Zames.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
        blocks = BlockProduction.objects.filter(date__gte=start_date, date__lte=end_date)
        total_input = zames.aggregate(total=Sum('input_weight'))['total'] or 0
        total_output = zames.aggregate(total=Sum('output_weight'))['total'] or 0
        total_blocks = blocks.aggregate(total=Sum('block_count'))['total'] or 0
        efficiency = round((total_output / total_input) * 100, 2) if total_input else 0
        return [
            ['Ko\'rsatkich', 'Qiymat'],
            ['Zames soni', zames.count()],
            ['Jami input (kg)', total_input],
            ['Jami output (kg)', total_output],
            ['Bloklar soni', total_blocks],
            ['Samaradorlik (%)', efficiency],
        ]

    if report_type == 'WASTE':
        waste = WasteProcessing.objects.filter(date__date__gte=start_date, date__date__lte=end_date)
        grouped = waste.values('source_department').annotate(
            total_kg=Sum('waste_amount_kg'),
            count=Count('id'),
        ).order_by('source_department')
        rows = [['Bo\'lim', 'Qaydlar', 'Chiqindi (kg)']]
        total_waste = 0
        for row in grouped:
            total_waste += row['total_kg'] or 0
            rows.append([row['source_department'], row['count'], row['total_kg'] or 0])
        rows.append([])
        rows.append(['Jami', '', total_waste])
        return rows

    intake = RawMaterialBatch.objects.filter(date__gte=start_date, date__lte=end_date)
    return [
        ['Ko\'rsatkich', 'Qiymat'],
        ['Batchlar soni', intake.count()],
        ['Jami kirim (kg)', intake.aggregate(total=Sum('quantity_kg'))['total'] or 0],
    ]


def rows_to_csv_bytes(rows):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(rows)
    return output.getvalue().encode('utf-8-sig')


def _escape_pdf_text(value: str):
    return value.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def rows_to_pdf_bytes(title: str, rows):
    lines = [title, '']
    for row in rows:
        if not row:
            lines.append('')
            continue
        line = ' | '.join(str(cell) for cell in row)
        lines.extend(textwrap.wrap(line, width=90) or [''])

    y = 790
    content_lines = ['BT', '/F1 11 Tf', '14 TL', f'50 {y} Td']
    for line in lines[:48]:
        content_lines.append(f'({_escape_pdf_text(line)}) Tj')
        content_lines.append('T*')
    content_lines.append('ET')
    stream = '\n'.join(content_lines).encode('latin-1', errors='replace')

    objects = [
        b'1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj',
        b'2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj',
        b'3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj',
        f'4 0 obj << /Length {len(stream)} >> stream\n'.encode('latin-1') + stream + b'\nendstream endobj',
        b'5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj',
    ]

    pdf = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
        pdf.extend(b'\n')
    xref_offset = len(pdf)
    pdf.extend(f'xref\n0 {len(offsets)}\n'.encode('latin-1'))
    pdf.extend(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        pdf.extend(f'{offset:010d} 00000 n \n'.encode('latin-1'))
    pdf.extend(
        f'trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF'.encode('latin-1')
    )
    return bytes(pdf)


def build_export_response_content(title: str, rows, file_format: str):
    """
    Helper for views to quickly generate content, extension, and content_type.
    """
    if file_format == 'EXCEL' or file_format == 'CSV':
        content = rows_to_csv_bytes(rows)
        return content, 'csv', 'text/csv'
    
    # Default to PDF
    content = rows_to_pdf_bytes(title, rows)
    return content, 'pdf', 'application/pdf'


def generate_report_file(report_history):
    start_date, end_date = _parse_period(report_history.period)
    rows = _build_rows(report_history.report_type, start_date, end_date)
    title = f'{report_history.name} ({start_date} - {end_date})'

    if report_history.file_format == 'EXCEL':
        content = rows_to_csv_bytes(rows)
        extension = 'csv'
    else:
        content = rows_to_pdf_bytes(title, rows)
        extension = 'pdf'

    filename = f"{report_history.report_type.lower()}-{timezone.now().strftime('%Y%m%d%H%M%S')}.{extension}"
    report_history.file_path.save(filename, ContentFile(content), save=False)
    report_history.file_size = f'{max(len(content) // 1024, 1)} KB'
    report_history.status = 'READY'
    report_history.save(update_fields=['file_path', 'file_size', 'status'])
    return report_history


def get_inventory_valuation():
    """
    Calculates total stock value (money in warehouses).
    Uses real batch unit costs where available.
    """
    from production_v2.models import ProductionBatch
    
    stocks = Stock.objects.select_related('material', 'warehouse')
    total_value = Decimal('0')
    
    # Pre-fetch latest batch costs for finished materials to avoid N+1
    # We take the latest CLOSED batch for each material type (usually blocks)
    # Since blocks are products, we check ProductionBatch which has the unit_cost
    latest_costs = {}
    
    for s in stocks:
        unit_price = s.material.price or Decimal('0')
        
        if s.material.category == 'FINISHED':
            # Check if we have a cached last cost for this product's batches
            if s.material.id not in latest_costs:
                # Find latest closed batch that produced this type of material
                # Note: ProductionBatch doesn't link to Material directly, but output does.
                # As a shortcut, we take the most recent batch's unit_cost for all finished goods
                # unless further granular mapping is implemented.
                latest_pb = ProductionBatch.objects.filter(status='CLOSED').order_by('-end_time').first()
                if latest_pb:
                    latest_costs[s.material.id] = latest_pb.unit_cost
                else:
                    latest_costs[s.material.id] = unit_price
            
            unit_price = latest_costs.get(s.material.id, unit_price)
            
        value = Decimal(str(s.quantity)) * unit_price
        total_value += value
        
    return total_value

def get_profitability_summary(period='This Month'):
    """
    Aggregates profit, margin, and identifies loss-making products.
    """
    start_date, end_date = _parse_period(period)
    invoices = Invoice.objects.filter(
        date__date__gte=start_date, 
        date__date__lte=end_date,
        status='COMPLETED'
    )
    
    metrics = {
        'total_revenue': invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0'),
        'total_profit': invoices.aggregate(Sum('total_profit'))['total_profit__sum'] or Decimal('0'),
        'avg_margin': 0,
        'loss_count': invoices.filter(total_profit__lt=0).count(),
        'low_margin_count': invoices.filter(avg_margin_percent__lt=15).count(),
    }
    
    if metrics['total_revenue'] > 0:
        metrics['avg_margin'] = round((metrics['total_profit'] / metrics['total_revenue']) * 100, 2)
        
    return metrics

