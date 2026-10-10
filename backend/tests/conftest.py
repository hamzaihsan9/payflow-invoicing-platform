import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.main import app
from app.database import Base, get_db
from app.models.models import User, UserRole, Client as ClientModel
from app.services.auth_service import get_password_hash

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_suite.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def prepare_test_db():
    Base.metadata.create_all(bind=engine)
    
    # Pre-seed standard test entities
    db = TestingSessionLocal()
    if not db.query(User).filter(User.email == "admin@payflow.pk").first():
        admin = User(
            email="admin@payflow.pk",
            hashed_password=get_password_hash("Admin123!"),
            full_name="Admin Controller",
            role=UserRole.ADMIN,
            organization="PayFlow Controller",
            is_active=True
        )
        db.add(admin)

    if not db.query(ClientModel).filter(ClientModel.company == "Systems Limited").first():
        corp = ClientModel(
            company="Systems Limited",
            name="Asif Peer",
            email="accounts@systemsltd.com",
            phone="+92-42-111-797-836",
            tax_id="NTN-0814920-1",
            address="Lahore, Pakistan"
        )
        db.add(corp)
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass

@pytest.fixture
def client():
    return TestClient(app)
