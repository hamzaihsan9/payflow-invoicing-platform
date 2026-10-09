import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "PayFlow Pro Enterprise Invoicing"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Database configuration (Defaults to SQLite for instant local execution, overrides with Postgres in Docker)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./payflow.db")
    
    # JWT Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-enterprise-jwt-key-for-pakistan-it-industry-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours
    
    # Microservice Webhook Worker URL (Node.js service)
    NODE_WORKER_URL: str = os.getenv("NODE_WORKER_URL", "http://localhost:5001")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
