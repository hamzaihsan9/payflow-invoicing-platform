import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, 
    Enum, Text, Boolean
)
from sqlalchemy.orm import relationship
from app.database import Base

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    FINANCE_MANAGER = "FINANCE_MANAGER"
    AUDITOR = "AUDITOR"
    CLIENT = "CLIENT"

class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.FINANCE_MANAGER, nullable=False)
    organization = Column(String(255), default="Systems & Cloud Enterprises Ltd")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    invoices = relationship("Invoice", back_populates="creator")
    audit_logs = relationship("AuditLog", back_populates="user")

class Client(Base):
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    email = Column(String(255), index=True, nullable=False)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    tax_id = Column(String(100), nullable=True) # NTN / STRN / Tax Registration
    created_at = Column(DateTime, default=datetime.utcnow)
    
    invoices = relationship("Invoice", back_populates="client", cascade="all, delete-orphan")

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(100), unique=True, index=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.ISSUED, nullable=False)
    issue_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    currency = Column(String(10), default="PKR") # PKR, USD, EUR, AED
    subtotal = Column(Float, default=0.0)
    tax_rate = Column(Float, default=0.16) # e.g. 16% PRA / FBR sales tax
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    client = relationship("Client", back_populates="invoices")
    creator = relationship("User", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    description = Column(String(255), nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    
    invoice = relationship("Invoice", back_populates="items")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50), default="BANK_TRANSFER") # IBFT, RAAS, STRIPE, CASH
    reference_no = Column(String(100), nullable=True)
    paid_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    
    invoice = relationship("Invoice", back_populates="payments")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False) # e.g. INVOICE_CREATED, PAYMENT_RECEIVED
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="audit_logs")
