from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User
from app.services.auth_service import get_current_user
from app.services.paybot_service import PayBotEngine, GEMINI_TOOLS
from app.config import settings

router = APIRouter(prefix="/paybot", tags=["PayBot AI Autonomous Agent"])

class ChatMessage(BaseModel):
    role: str # "user" or "model" / "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    api_key: Optional[str] = None

class ActionPayload(BaseModel):
    type: str
    invoice_id: Optional[int] = None
    invoice_number: Optional[str] = None
    client_company: Optional[str] = None
    total_amount: Optional[float] = None
    status: Optional[str] = None
    pdf_url: Optional[str] = None
    flagged_count: Optional[int] = None
    total_overdue_pkr: Optional[float] = None

class ChatResponse(BaseModel):
    response: str
    action_taken: Optional[Dict[str, Any]] = None
    source: str
    model: Optional[str] = None
    suggested_prompts: List[str]

class ConfigUpdateRequest(BaseModel):
    api_key: str
    model: Optional[str] = "gemini-2.5-flash"

@router.post("/chat", response_model=ChatResponse)
async def chat_with_paybot(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Primary conversational automation endpoint.
    Processes user intent, calls tools against PayFlow, and generates an executive response.
    """
    history_dicts = [{"role": h.role, "content": h.content} for h in (payload.history or [])]
    
    result = await PayBotEngine.chat(
        user_message=payload.message,
        history=history_dicts,
        db=db,
        current_user=current_user,
        custom_api_key=payload.api_key
    )
    
    return ChatResponse(
        response=result.get("response", ""),
        action_taken=result.get("action_taken"),
        source=result.get("source", "local_autonomous"),
        model=result.get("model", settings.GEMINI_MODEL),
        suggested_prompts=result.get("suggested_prompts", [])
    )

@router.get("/status")
def get_paybot_status():
    """
    Returns PayBot operational status, Gemini connectivity configuration, and registered tool specs.
    """
    has_env_key = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
    return {
        "status": "online",
        "name": "PayBot",
        "role": "Autonomous Corporate Financial Operations & Invoicing AI",
        "has_gemini_key": has_env_key,
        "model": settings.GEMINI_MODEL,
        "available_tools": [t["name"] for t in GEMINI_TOOLS],
        "tool_definitions": GEMINI_TOOLS,
        "capabilities": [
            "Autonomous Corporate Tax Invoice Creation (PRA 16%)",
            "Multi-Entity Receivables Reconciliation & Aging Analysis",
            "Dynamic Status Updates & Immutable Audit Logging",
            "ReportLab Corporate Tax PDF Streaming",
            "Counterparty Remittance Tracking (RAAST & IBFT)"
        ]
    }

@router.post("/reconcile")
async def trigger_autonomous_reconciliation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    1-Click autonomous sweep to inspect receivables, flag overdue invoices, and compute risk analysis.
    """
    res, action = await PayBotEngine.execute_tool("auto_reconcile_overdue", {}, db, current_user)
    return {
        "success": True,
        "results": res,
        "action": action
    }

@router.post("/config")
def update_gemini_config(payload: ConfigUpdateRequest):
    """
    Update the runtime Gemini API configuration.
    """
    key = payload.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API key cannot be empty")
    
    settings.GEMINI_API_KEY = key
    if payload.model:
        settings.GEMINI_MODEL = payload.model.strip()
        
    return {
        "success": True,
        "message": "Gemini API key updated successfully.",
        "model": settings.GEMINI_MODEL
    }
