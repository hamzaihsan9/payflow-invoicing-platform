from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Invoice, InvoiceItem, Payment, Client, User, UserRole, InvoiceStatus
from app.schemas.schemas import (
    InvoiceCreate, InvoiceUpdate, InvoiceResponse, PaymentCreate, PaymentResponse
)
from app.services.auth_service import get_current_user, require_roles, record_audit_log
from app.services.invoice_service import (
    generate_invoice_number, calculate_invoice_totals, 
    notify_node_worker, generate_invoice_pdf_buffer
)

router = APIRouter(prefix="/invoices", tags=["Invoices & Billing"])

@router.get("/", response_model=List[InvoiceResponse])
def list_invoices(
    status_filter: Optional[InvoiceStatus] = Query(None, alias="status"),
    client_id: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Invoice)
    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    if client_id:
        query = query.filter(Invoice.client_id == client_id)
    return query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()

@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_in: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.FINANCE_MANAGER]))
):
    client = db.query(Client).filter(Client.id == invoice_in.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client does not exist")
    
    if not invoice_in.items:
        raise HTTPException(status_code=400, detail="An invoice must contain at least one line item")

    subtotal, tax_amount, total_amount = calculate_invoice_totals(
        invoice_in.items, invoice_in.tax_rate
    )
    invoice_number = generate_invoice_number(db)

    invoice = Invoice(
        invoice_number=invoice_number,
        client_id=client.id,
        created_by_id=current_user.id,
        status=InvoiceStatus.ISSUED,
        issue_date=datetime.utcnow(),
        due_date=invoice_in.due_date,
        currency=invoice_in.currency,
        subtotal=subtotal,
        tax_rate=invoice_in.tax_rate,
        tax_amount=tax_amount,
        total_amount=total_amount,
        notes=invoice_in.notes
    )
    db.add(invoice)
    db.flush()

    for item_data in invoice_in.items:
        line_total = round(item_data.quantity * item_data.unit_price, 2)
        item = InvoiceItem(
            invoice_id=invoice.id,
            description=item_data.description,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            total=line_total
        )
        db.add(item)
    
    db.commit()
    db.refresh(invoice)

    record_audit_log(
        db, current_user.id, "INVOICE_ISSUED", "INVOICE", str(invoice.id),
        f"Issued invoice {invoice.invoice_number} for {invoice.currency} {invoice.total_amount:,.2f}"
    )

    # Polyglot notification to Node.js worker service
    await notify_node_worker("INVOICE_CREATED", {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "client_email": client.email,
        "amount": invoice.total_amount,
        "currency": invoice.currency
    })

    return invoice

@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@router.patch("/{invoice_id}/status", response_model=InvoiceResponse)
def update_invoice_status(
    invoice_id: int,
    status_update: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.FINANCE_MANAGER]))
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if status_update.status:
        old_status = invoice.status.value
        invoice.status = status_update.status
        record_audit_log(
            db, current_user.id, "STATUS_CHANGE", "INVOICE", str(invoice.id),
            f"Changed invoice {invoice.invoice_number} status from {old_status} to {status_update.status.value}"
        )
    if status_update.notes is not None:
        invoice.notes = status_update.notes

    db.commit()
    db.refresh(invoice)
    return invoice

@router.post("/{invoice_id}/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_payment(
    invoice_id: int,
    payment_in: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.FINANCE_MANAGER]))
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    payment = Payment(
        invoice_id=invoice.id,
        amount=payment_in.amount,
        payment_method=payment_in.payment_method,
        reference_no=payment_in.reference_no,
        notes=payment_in.notes,
        paid_at=datetime.utcnow()
    )
    db.add(payment)
    
    # Check if sum of payments satisfies invoice total
    total_paid = sum(p.amount for p in invoice.payments) + payment.amount
    if total_paid >= invoice.total_amount:
        invoice.status = InvoiceStatus.PAID
    
    db.commit()
    db.refresh(payment)

    record_audit_log(
        db, current_user.id, "PAYMENT_RECORDED", "INVOICE", str(invoice.id),
        f"Recorded payment of {invoice.currency} {payment.amount:,.2f} on {invoice.invoice_number}"
    )

    await notify_node_worker("PAYMENT_RECEIVED", {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "amount_received": payment.amount,
        "total_paid": total_paid,
        "status": invoice.status.value
    })

    return payment

@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    pdf_buffer = generate_invoice_pdf_buffer(invoice)
    filename = f"{invoice.invoice_number}.pdf"
    
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-cache"
        }
    )
