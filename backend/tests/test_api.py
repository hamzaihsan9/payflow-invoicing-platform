import pytest
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.services.invoice_service import calculate_invoice_totals

# In-memory test DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_payflow.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_math_calculation():
    class ItemMock:
        def __init__(self, qty, price):
            self.quantity = qty
            self.unit_price = price
    
    items = [ItemMock(2.0, 50000.0), ItemMock(1.0, 25000.0)]
    subtotal, tax, total = calculate_invoice_totals(items, 0.16)
    
    assert subtotal == 125000.0
    assert tax == 20000.0
    assert total == 145000.0

def test_user_registration_and_login():
    # Register
    reg_res = client.post("/api/v1/auth/register", json={
        "email": "finance@enterprise.pk",
        "password": "Password123!",
        "full_name": "Test Finance Officer",
        "role": "FINANCE_MANAGER",
        "organization": "Enterprise PK"
    })
    assert reg_res.status_code == 201
    assert reg_res.json()["email"] == "finance@enterprise.pk"

    # Login
    login_res = client.post("/api/v1/auth/login", data={
        "username": "finance@enterprise.pk",
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()
