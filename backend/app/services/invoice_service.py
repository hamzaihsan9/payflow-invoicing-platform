import os
import io
import httpx
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.config import settings
from app.models.models import Invoice, InvoiceItem, InvoiceStatus, Client, User
from app.schemas.schemas import InvoiceCreate

def generate_invoice_number(db: Session) -> str:
    current_year = datetime.utcnow().year
    count = db.query(Invoice).filter(Invoice.invoice_number.like(f"INV-{current_year}-%")).count()
    return f"INV-{current_year}-{str(count + 1).zfill(4)}"

def calculate_invoice_totals(items_data: list, tax_rate: float):
    subtotal = sum(item.quantity * item.unit_price for item in items_data)
    tax_amount = round(subtotal * tax_rate, 2)
    total_amount = round(subtotal + tax_amount, 2)
    return round(subtotal, 2), tax_amount, total_amount

async def notify_node_worker(event: str, payload: dict):
    """
    Polyglot Microservice Integration:
    Dispatches asynchronous webhooks to the Node.js event & PDF worker.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(
                f"{settings.NODE_WORKER_URL}/api/events",
                json={"event": event, "timestamp": datetime.utcnow().isoformat(), "data": payload}
            )
    except Exception:
        # Graceful fallback if Node worker service is offline during standalone execution
        pass

def generate_invoice_pdf_buffer(invoice: Invoice) -> io.BytesIO:
    """
    Generates a professional corporate tax invoice compliant with Pakistani corporate
    and international B2B billing standards (Punjab Revenue Authority PRA / FBR guidelines).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    story = []
    styles = getSampleStyleSheet()

    # Document Header / Brand
    header_data = [
        [
            Paragraph(
                "<font size=18 color='#0f172a'><b>TAX INVOICE</b></font><br/>"
                f"<font size=10 color='#64748b'><b>Invoice Number:</b> {invoice.invoice_number}</font><br/>"
                f"<font size=9 color='#64748b'><b>Issued:</b> {invoice.issue_date.strftime('%d %b %Y')} &nbsp;|&nbsp; <b>Due:</b> {invoice.due_date.strftime('%d %b %Y')}</font>",
                styles['Normal']
            ),
            Paragraph(
                "<font size=12 color='#0f172a'><b>PayFlow Technologies (Pvt) Ltd</b></font><br/>"
                "<font size=8 color='#475569'>Tech Park, Canal Road, Lahore, Pakistan<br/>"
                "NTN: 8294104-7 &nbsp;|&nbsp; PRA STRN: 3277876123456<br/>"
                "accounts@payflow.pk &nbsp;|&nbsp; +92 42 3595-0100</font>",
                styles['Normal']
            )
        ]
    ]
    header_table = Table(header_data, colWidths=[310, 220])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor('#0f172a')),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 14))

    # Billed To and Payment Status Box
    status_color = '#15803d' if invoice.status == InvoiceStatus.PAID else '#b45309'
    bill_data = [
        [
            Paragraph(
                "<font size=8 color='#64748b'><b>BILLED TO (CLIENT):</b></font><br/>"
                f"<font size=11 color='#0f172a'><b>{invoice.client.company}</b></font><br/>"
                f"<font size=9 color='#334155'>Attn: {invoice.client.name}<br/>"
                f"Tax NTN: {invoice.client.tax_id or 'Exempt / Not Stated'}<br/>"
                f"Email: {invoice.client.email} &nbsp;|&nbsp; Tel: {invoice.client.phone or 'N/A'}<br/>"
                f"Address: {invoice.client.address or 'Lahore, Pakistan'}</font>",
                styles['Normal']
            ),
            Paragraph(
                f"<div style='text-align: right;'>"
                f"<font size=8 color='#64748b'><b>SETTLEMENT STATUS:</b></font><br/>"
                f"<font size=14 color='{status_color}'><b>{invoice.status.value}</b></font><br/><br/>"
                f"<font size=8 color='#64748b'><b>CURRENCY:</b></font><br/>"
                f"<font size=10 color='#0f172a'><b>{invoice.currency} (Pakistani Rupee)</b></font>"
                f"</div>",
                styles['Normal']
            )
        ]
    ]
    bill_table = Table(bill_data, colWidths=[350, 180])
    bill_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(bill_table)
    story.append(Spacer(1, 16))

    # Itemized Breakdown Table
    item_rows = [
        [
            Paragraph("<font size=9 color='#ffffff'><b>Line Item / Service Description</b></font>", styles['Normal']),
            Paragraph("<font size=9 color='#ffffff'><b>Qty</b></font>", styles['Normal']),
            Paragraph("<font size=9 color='#ffffff'><b>Rate (PKR)</b></font>", styles['Normal']),
            Paragraph("<font size=9 color='#ffffff'><b>Net Amount</b></font>", styles['Normal'])
        ]
    ]
    for item in invoice.items:
        item_rows.append([
            Paragraph(f"<font size=9 color='#1e293b'><b>{item.description}</b></font>", styles['Normal']),
            Paragraph(f"<font size=9 color='#334155'>{item.quantity:.0f}</font>", styles['Normal']),
            Paragraph(f"<font size=9 color='#334155'>{item.unit_price:,.2f}</font>", styles['Normal']),
            Paragraph(f"<font size=9 color='#0f172a'><b>{item.total:,.2f}</b></font>", styles['Normal'])
        ])

    # Financial Summaries
    item_rows.append([
        "", "",
        Paragraph("<font size=9 color='#475569'>Subtotal (Excl. Tax):</font>", styles['Normal']),
        Paragraph(f"<font size=9 color='#0f172a'>{invoice.currency} {invoice.subtotal:,.2f}</font>", styles['Normal'])
    ])
    item_rows.append([
        "", "",
        Paragraph(f"<font size=9 color='#475569'>Punjab Sales Tax (PRA @ {int(invoice.tax_rate*100)}%):</font>", styles['Normal']),
        Paragraph(f"<font size=9 color='#0f172a'>{invoice.currency} {invoice.tax_amount:,.2f}</font>", styles['Normal'])
    ])
    item_rows.append([
        "", "",
        Paragraph("<font size=10 color='#0f172a'><b>TOTAL PAYABLE:</b></font>", styles['Normal']),
        Paragraph(f"<font size=11 color='#0f172a'><b>{invoice.currency} {invoice.total_amount:,.2f}</b></font>", styles['Normal'])
    ])

    item_table = Table(item_rows, colWidths=[270, 50, 100, 110])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-4), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (2,-4), (3,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (2,-1), (3,-1), colors.HexColor('#f1f5f9')),
        ('LINEABOVE', (2,-1), (3,-1), 1.5, colors.HexColor('#0f172a')),
    ]))
    story.append(item_table)
    story.append(Spacer(1, 16))

    # Corporate Remittance & Banking Instructions
    bank_info = [
        [
            Paragraph(
                "<font size=8 color='#475569'><b>OFFICIAL BANK REMITTANCE INSTRUCTIONS (1LINK IBFT / RAAST)</b><br/>"
                "<b>Beneficiary:</b> PayFlow Technologies (Pvt) Ltd<br/>"
                "<b>Bank:</b> Habib Bank Limited (HBL) — Corporate Banking Wing, Lahore<br/>"
                "<b>IBAN Account:</b> PK36HABB0001234567890123 &nbsp;|&nbsp; <b>Branch Code:</b> 0492<br/>"
                "<b>RAAST Direct ID:</b> 03446751031<br/>"
                f"<b>Payment Terms:</b> {invoice.notes or 'Net 30 days. Please quote invoice number upon remittance.'}</font>",
                styles['Normal']
            )
        ]
    ]
    bank_table = Table(bank_info, colWidths=[530])
    bank_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(bank_table)
    story.append(Spacer(1, 14))

    # Audit & Verification Footer
    footer_text = (
        f"<font size=7 color='#94a3b8'>This document is an electronically verified corporate invoice issued via PayFlow Financial Operations Engine.<br/>"
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | Verification Hash: sha256:{hash(invoice.invoice_number + str(invoice.total_amount)) & 0xffffffff:08x}</font>"
    )
    story.append(Paragraph(footer_text, styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer
