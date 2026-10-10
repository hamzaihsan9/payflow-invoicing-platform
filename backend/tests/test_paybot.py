import pytest

def test_paybot_status(client):
    res = client.get("/api/v1/paybot/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert data["name"] == "PayBot"
    assert "create_invoice" in data["available_tools"]
    assert "get_financial_summary" in data["available_tools"]

def test_paybot_chat_financial_summary(client):
    res = client.post("/api/v1/paybot/chat", json={
        "message": "Give me the executive financial summary"
    })
    assert res.status_code == 200
    data = res.json()
    assert "PayFlow Executive Financial Summary" in data["response"]
    assert "Total Billed" in data["response"]

def test_paybot_chat_create_invoice(client):
    res = client.post("/api/v1/paybot/chat", json={
        "message": "Create invoice for Systems Limited for 250000 PKR for Cloud Engineering"
    })
    assert res.status_code == 200
    data = res.json()
    assert "Corporate Tax Invoice Issued" in data["response"]
    assert data["action_taken"] is not None
    assert data["action_taken"]["type"] == "invoice_created"
    assert data["action_taken"]["client_company"] == "Systems Limited"

def test_paybot_chat_mark_paid(client):
    # First create invoice
    create_res = client.post("/api/v1/paybot/chat", json={
        "message": "Create invoice for Systems Limited for 100000 PKR"
    })
    inv_num = create_res.json()["action_taken"]["invoice_number"]

    # Mark as paid
    pay_res = client.post("/api/v1/paybot/chat", json={
        "message": f"Mark invoice {inv_num} as paid"
    })
    assert pay_res.status_code == 200
    data = pay_res.json()
    assert "Remittance Confirmed" in data["response"]
    assert data["action_taken"]["type"] == "status_updated"
    assert data["action_taken"]["status"] == "PAID"

def test_paybot_auto_reconcile(client):
    res = client.post("/api/v1/paybot/reconcile")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "results" in data

def test_paybot_config_update(client):
    res = client.post("/api/v1/paybot/config", json={
        "api_key": "test-gemini-key-12345",
        "model": "gemini-2.5-flash"
    })
    assert res.status_code == 200
    assert res.json()["success"] is True
