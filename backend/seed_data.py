import sys
import os
from datetime import datetime, timedelta

# Append app root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, Base, engine
from app.models.models import User, Client, Invoice, InvoiceItem, Payment, UserRole, InvoiceStatus
from app.services.auth_service import get_password_hash

def seed():
    print("🌱 Initializing PayFlow Pro Database Tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 1. Seed Admin & Finance Users
    admin_email = "admin@payflow.pk"
    admin = db.query(User).filter(User.email == admin_email).first()
    if not admin:
        print("👤 Creating default Admin user...")
        admin = User(
            email=admin_email,
            hashed_password=get_password_hash("Admin@123456"),
            full_name="Hamza Ihsan (Lead Engineer)",
            role=UserRole.ADMIN,
            organization="PayFlow Enterprise Solutions"
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

    # 2. Seed Corporate Clients
    client_companies = [
        {"name": "Asif Peer", "company": "Systems Limited", "email": "accounts@systemsltd.com", "phone": "+92-42-111-797-836", "address": "E-5, Central Commercial Area, DHA Phase 1, Lahore", "tax_id": "NTN-0814920-1"},
        {"name": "Aamir Ibrahim", "company": "Jazz Telecom (PMCL)", "email": "procurement@jazz.com.pk", "phone": "+92-51-111-300-300", "address": "Jazz HQ, G-8/4, Islamabad", "tax_id": "NTN-0710123-4"},
        {"name": "Yasser Bashir", "company": "Arbisoft Technologies", "email": "billing@arbisoft.com", "phone": "+92-42-35954601", "address": "25-C, Canal Bank Road, Lahore", "tax_id": "NTN-2938472-8"},
        {"name": "Zeeshan Aftab", "company": "10Pearls Pakistan", "email": "finance.pk@10pearls.com", "phone": "+92-21-34328571", "address": "Shahrah-e-Faisal, PECHS Block 6, Karachi", "tax_id": "NTN-3849102-5"}
    ]

    seeded_clients = []
    for c_data in client_companies:
        client = db.query(Client).filter(Client.email == c_data["email"]).first()
        if not client:
            client = Client(**c_data)
            db.add(client)
            db.commit()
            db.refresh(client)
        seeded_clients.append(client)

    # 3. Seed Sample Invoices
    if db.query(Invoice).count() == 0:
        print("📄 Seeding sample production invoices...")
        
        # Invoice 1: Paid Cloud Architecture
        c1 = seeded_clients[0]
        inv1 = Invoice(
            invoice_number="INV-2026-0001",
            client_id=c1.id,
            created_by_id=admin.id,
            status=InvoiceStatus.PAID,
            issue_date=datetime.utcnow() - timedelta(days=20),
            due_date=datetime.utcnow() - timedelta(days=5),
            currency="PKR",
            subtotal=750000.0,
            tax_rate=0.16,
            tax_amount=120000.0,
            total_amount=870000.0,
            notes="Quarterly Kubernetes Cluster & FastAPI Microservice Architecture Consultation"
        )
        db.add(inv1)
        db.flush()
        db.add(InvoiceItem(invoice_id=inv1.id, description="Microservice Engineering (Sprints 1-4)", quantity=4.0, unit_price=150000.0, total=600000.0))
        db.add(InvoiceItem(invoice_id=inv1.id, description="High-Availability Redis & DB Clustering", quantity=1.0, unit_price=150000.0, total=150000.0))
        db.add(Payment(invoice_id=inv1.id, amount=870000.0, payment_method="RAAST_INSTANT", reference_no="RAAST-TX-982144"))

        # Invoice 2: Issued Mobile Platform
        c2 = seeded_clients[1]
        inv2 = Invoice(
            invoice_number="INV-2026-0002",
            client_id=c2.id,
            created_by_id=admin.id,
            status=InvoiceStatus.ISSUED,
            issue_date=datetime.utcnow() - timedelta(days=5),
            due_date=datetime.utcnow() + timedelta(days=15),
            currency="PKR",
            subtotal=480000.0,
            tax_rate=0.16,
            tax_amount=76800.0,
            total_amount=556800.0,
            notes="Enterprise B2B Telemetry & Portal Integration"
        )
        db.add(inv2)
        db.flush()
        db.add(InvoiceItem(invoice_id=inv2.id, description="React & Vue Portal Development", quantity=2.0, unit_price=180000.0, total=360000.0))
        db.add(InvoiceItem(invoice_id=inv2.id, description="REST API Rate Limiting & Auth Hardening", quantity=1.0, unit_price=120000.0, total=120000.0))

        # Invoice 3: Overdue AI Models
        c3 = seeded_clients[2]
        inv3 = Invoice(
            invoice_number="INV-2026-0003",
            client_id=c3.id,
            created_by_id=admin.id,
            status=InvoiceStatus.OVERDUE,
            issue_date=datetime.utcnow() - timedelta(days=40),
            due_date=datetime.utcnow() - timedelta(days=10),
            currency="PKR",
            subtotal=920000.0,
            tax_rate=0.16,
            tax_amount=147200.0,
            total_amount=1067200.0,
            notes="Custom BERT Intent Classifier Training & Inference Pipeline"
        )
        db.add(inv3)
        db.flush()
        db.add(InvoiceItem(invoice_id=inv3.id, description="BERT Model Fine-Tuning & Evaluation", quantity=1.0, unit_price=600000.0, total=600000.0))
        db.add(InvoiceItem(invoice_id=inv3.id, description="Production Containerized Inference Engine", quantity=1.0, unit_price=320000.0, total=320000.0))

        db.commit()

    db.close()
    print("✅ Database seeding completed successfully!")

if __name__ == "__main__":
    seed()
