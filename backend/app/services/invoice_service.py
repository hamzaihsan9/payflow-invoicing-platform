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
    Generates a professional corporate PDF invoice matching corporate standards in Pakistan.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    # Branded Header
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#1793d1'),
        fontName='Helvetica-Bold'
    )
    story.append(Paragraph(f"INVOICE // {invoice.invoice_number}", title_style))
    story.append(Spacer(1, 10))

    # Organization & Client Info Table
    meta_data = [
        [
            Paragraph(f"<b>ISSUER:</b><br/>Systems &amp; Cloud Operations Ltd<br/>Lahore Tech Park, Pakistan<br/>NTN: 8294104-7", styles['Normal']),
            Paragraph(f"<b>BILLED TO:</b><br/>{invoice.client.company}<br/>Attn: {invoice.client.name}<br/>{invoice.client.email}<br/>{invoice.client.phone or ''}", styles['Normal'])
        ],
        [
            Paragraph(f"<b>Issue Date:</b> {invoice.issue_date.strftime('%Y-%m-%d')}<br/><b>Due Date:</b> {invoice.due_date.strftime('%Y-%m-%d')}", styles['Normal']),
            Paragraph(f"<b>Status:</b> {invoice.status.value}<br/><b>Currency:</b> {invoice.currency}", styles['Normal'])
        ]
    ]
    meta_table = Table(meta_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # Items Table
    item_rows = [["Description", "Qty", "Unit Price", "Total"]]
    for item in invoice.items:
        item_rows.append([
            item.description,
            f"{item.quantity:.1f}",
            f"{invoice.currency} {item.unit_price:,.2f}",
            f"{invoice.currency} {item.total:,.2f}"
        ])
    
    # Summary Totals
    item_rows.append(["", "", "Subtotal:", f"{invoice.currency} {invoice.subtotal:,.2f}"])
    item_rows.append(["", "", f"Sales Tax ({int(invoice.tax_rate*100)}%):", f"{invoice.currency} {invoice.tax_amount:,.2f}"])
    item_rows.append(["", "", "GRAND TOTAL:", f"{invoice.currency} {invoice.total_amount:,.2f}"])

    item_table = Table(item_rows, colWidths=[270, 60, 110, 100])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1c2436')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-4), 0.5, colors.HexColor('#cbd5e1')),
        ('LINEABOVE', (2,-3), (3,-1), 1, colors.HexColor('#1793d1')),
        ('FONTNAME', (2,-1), (3,-1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(item_table)

    if invoice.notes:
        story.append(Spacer(1, 20))
        story.append(Paragraph(f"<b>Notes &amp; Remittance Details:</b><br/>{invoice.notes}", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer
