from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Client, User, UserRole
from app.schemas.schemas import ClientCreate, ClientUpdate, ClientResponse
from app.services.auth_service import get_current_user, require_roles, record_audit_log

router = APIRouter(prefix="/clients", tags=["Clients & Accounts"])

@router.get("/", response_model=List[ClientResponse])
def list_clients(
    search: Optional[str] = Query(None, description="Search by name, company, or email"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Client)
    if search:
        term = f"%{search}%"
        query = query.filter(
            (Client.name.ilike(term)) | 
            (Client.company.ilike(term)) | 
            (Client.email.ilike(term))
        )
    return query.offset(skip).limit(limit).all()

@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client_in: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.FINANCE_MANAGER]))
):
    client = Client(**client_in.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)

    record_audit_log(
        db, current_user.id, "CLIENT_CREATED", "CLIENT", str(client.id),
        f"Registered new corporate client: {client.company} ({client.name})"
    )
    return client

@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    client_update: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.FINANCE_MANAGER]))
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = client_update.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(client, field, val)
    
    db.commit()
    db.refresh(client)
    record_audit_log(
        db, current_user.id, "CLIENT_UPDATED", "CLIENT", str(client.id),
        f"Updated corporate client details: {client.company}"
    )
    return client

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    db.delete(client)
    db.commit()
    record_audit_log(
        db, current_user.id, "CLIENT_DELETED", "CLIENT", str(client_id),
        f"Deleted client profile: {client.company}"
    )
    return None
