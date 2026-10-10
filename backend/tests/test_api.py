import pytest
from app.services.invoice_service import calculate_invoice_totals

def test_health_endpoint(client):
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

def test_user_registration_and_login(client):
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
