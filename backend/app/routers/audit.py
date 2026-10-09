from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import AuditLog, User, UserRole
from app.schemas.schemas import AuditLogResponse
from app.services.auth_service import require_roles

router = APIRouter(prefix="/audit", tags=["Compliance & Audit Logs"])

@router.get("/", response_model=List[AuditLogResponse])
def get_audit_trail(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.AUDITOR]))
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    
    result = []
    for log in logs:
        user_email = log.user.email if log.user else "System"
        result.append(AuditLogResponse(
            id=log.id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=log.details,
            timestamp=log.timestamp,
            user_email=user_email
        ))
    return result
