from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.models import Invoice, InvoiceStatus, User
from app.schemas.schemas import AnalyticsSummary
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/analytics", tags=["Financial Analytics"])

@router.get("/summary", response_model=AnalyticsSummary)
def get_analytics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invoices = db.query(Invoice).all()
    
    total_revenue = sum(inv.total_amount for inv in invoices if inv.status == InvoiceStatus.PAID)
    total_outstanding = sum(inv.total_amount for inv in invoices if inv.status in [InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE])
    
    paid_count = sum(1 for inv in invoices if inv.status == InvoiceStatus.PAID)
    issued_count = sum(1 for inv in invoices if inv.status == InvoiceStatus.ISSUED)
    overdue_count = sum(1 for inv in invoices if inv.status == InvoiceStatus.OVERDUE)

    return AnalyticsSummary(
        total_revenue=round(total_revenue, 2),
        total_outstanding=round(total_outstanding, 2),
        total_invoices=len(invoices),
        paid_count=paid_count,
        issued_count=issued_count,
        overdue_count=overdue_count,
        currency="PKR"
    )
