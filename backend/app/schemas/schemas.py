from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.models import UserRole, InvoiceStatus

# Authentication & User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    organization: Optional[str] = "TechOps Enterprise Ltd"
    role: UserRole = UserRole.FINANCE_MANAGER

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

# Client Schemas
class ClientBase(BaseModel):
    name: str
    company: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None

class ClientResponse(ClientBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Invoice Item Schemas
class InvoiceItemBase(BaseModel):
    description: str
    quantity: float = Field(default=1.0, gt=0)
    unit_price: float = Field(..., ge=0)

class InvoiceItemCreate(InvoiceItemBase):
    pass

class InvoiceItemResponse(InvoiceItemBase):
    id: int
    total: float

    class Config:
        from_attributes = True

# Payment Schemas
class PaymentBase(BaseModel):
    amount: float = Field(..., gt=0)
    payment_method: str = "BANK_TRANSFER"
    reference_no: Optional[str] = None
    notes: Optional[str] = None

class PaymentCreate(PaymentBase):
    pass

class PaymentResponse(PaymentBase):
    id: int
    invoice_id: int
    paid_at: datetime

    class Config:
        from_attributes = True

# Invoice Schemas
class InvoiceBase(BaseModel):
    client_id: int
    due_date: datetime
    currency: str = "PKR"
    tax_rate: float = Field(default=0.16, ge=0, le=1.0)
    notes: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    items: List[InvoiceItemCreate]

class InvoiceUpdate(BaseModel):
    status: Optional[InvoiceStatus] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None

class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    client_id: int
    client: ClientResponse
    status: InvoiceStatus
    issue_date: datetime
    due_date: datetime
    currency: str
    subtotal: float
    tax_rate: float
    tax_amount: float
    total_amount: float
    notes: Optional[str]
    created_at: datetime
    items: List[InvoiceItemResponse]
    payments: List[PaymentResponse]

    class Config:
        from_attributes = True

# Analytics Summary Schema
class AnalyticsSummary(BaseModel):
    total_revenue: float
    total_outstanding: float
    total_invoices: int
    paid_count: int
    issued_count: int
    overdue_count: int
    currency: str = "PKR"

# Audit Log Schema
class AuditLogResponse(BaseModel):
    id: int
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[str]
    timestamp: datetime
    user_email: Optional[str] = None

    class Config:
        from_attributes = True
