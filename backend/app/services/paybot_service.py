import os
import re
import json
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.models.models import (
    Invoice, InvoiceItem, Payment, Client, User, UserRole, 
    InvoiceStatus, AuditLog
)
from app.services.invoice_service import (
    generate_invoice_number, calculate_invoice_totals, 
    notify_node_worker
)
from app.services.auth_service import record_audit_log

SYSTEM_PROMPT = """You are PayBot, the automated corporate AI financial operations controller and invoicing agent for PayFlow.
Your expertise is in Pakistani corporate billing, sales tax compliance (Punjab Revenue Authority PRA 16% on services), receivables management, aging analysis, and automated ledger operations.

Platform Context:
- Currency: Pakistani Rupee (PKR).
- Standard PRA Sales Tax Rate: 16.0% on service deliverables.
- Corporate Settlement Channels: RAAST Instant ID (03446751031) and Habib Bank Limited IBAN (PK72HABB0001234567890123).
- Key Corporate Clients: Systems Limited, Jazz Telecom (PMCL), Arbisoft, 10Pearls Pakistan.

Behavior & Tone:
- You are autonomous, proactive, concise, and professional.
- When the user asks you to create an invoice, mark payments, reconcile accounts, or query data, EXECUTE THE TOOLS IMMEDIATELY.
- Always provide clear financial summaries, invoice numbers, line-item breakdowns, and direct action confirmations.
- If an invoice is created, format the result clearly with the invoice number, client name, subtotal, 16% PRA tax, total PKR, and mention that the ReportLab tax PDF is available.
- If asked to reconcile, run the automated reconciliation tool and report how many invoices were analyzed or flagged overdue.
"""

GEMINI_TOOLS = [
    {
        "name": "get_financial_summary",
        "description": "Retrieve executive financial KPIs including total revenue billed, settled receivables, outstanding balance, overdue invoice counts, and PRA sales tax metrics.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "list_invoices",
        "description": "Query live corporate invoices from the database with optional status filter or client search.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "status": {
                    "type": "STRING",
                    "description": "Filter by status: 'PAID', 'ISSUED', 'OVERDUE', or 'DRAFT'"
                },
                "client_name": {
                    "type": "STRING",
                    "description": "Filter by client company or contact name"
                },
                "limit": {
                    "type": "INTEGER",
                    "description": "Maximum records to return (default: 10)"
                }
            }
        }
    },
    {
        "name": "get_invoice_details",
        "description": "Fetch detailed information for a specific invoice by ID or invoice number (e.g. 'INV-2026-0001' or '1').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "invoice_identifier": {
                    "type": "STRING",
                    "description": "Invoice number (e.g. 'INV-2026-0001') or numeric ID (e.g. '1')"
                }
            },
            "required": ["invoice_identifier"]
        }
    },
    {
        "name": "create_invoice",
        "description": "Autonomously create a new corporate tax invoice for a client with line items, PRA 16% sales tax calculation, and event webhook dispatch.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "client_identifier": {
                    "type": "STRING",
                    "description": "Client company name, contact person, or numeric client ID (e.g. 'Systems Limited', 'Jazz Telecom', 'Arbisoft', '10Pearls')"
                },
                "items": {
                    "type": "ARRAY",
                    "description": "List of service deliverables or line items",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "description": { "type": "STRING", "description": "Description of work or deliverable" },
                            "quantity": { "type": "NUMBER", "description": "Quantity or sprint units (default 1)" },
                            "unit_price": { "type": "NUMBER", "description": "Unit rate in PKR" }
                        },
                        "required": ["description", "unit_price"]
                    }
                },
                "due_in_days": {
                    "type": "INTEGER",
                    "description": "Maturity term in days from today (default: 15)"
                },
                "notes": {
                    "type": "STRING",
                    "description": "Payment notes, purchase order references, or wire instructions"
                }
            },
            "required": ["client_identifier", "items"]
        }
    },
    {
        "name": "update_invoice_status",
        "description": "Update the status of an invoice to PAID, OVERDUE, ISSUED, or CANCELLED, with automated audit ledger logging.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "invoice_identifier": {
                    "type": "STRING",
                    "description": "Invoice number (e.g. 'INV-2026-0002') or numeric ID"
                },
                "new_status": {
                    "type": "STRING",
                    "description": "Target status: 'PAID', 'OVERDUE', 'ISSUED', or 'CANCELLED'"
                }
            },
            "required": ["invoice_identifier", "new_status"]
        }
    },
    {
        "name": "record_payment",
        "description": "Record a counterparty payment transaction (RAAST / IBFT / Bank Transfer) against an invoice and reconcile status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "invoice_identifier": {
                    "type": "STRING",
                    "description": "Invoice number or numeric ID"
                },
                "amount": {
                    "type": "NUMBER",
                    "description": "Remittance amount in PKR"
                },
                "payment_method": {
                    "type": "STRING",
                    "description": "Settlement method: 'RAAST', 'IBFT', or 'BANK_TRANSFER' (default: 'RAAST')"
                },
                "reference_no": {
                    "type": "STRING",
                    "description": "Bank transaction reference or RAAST tracking ID"
                },
                "notes": {
                    "type": "STRING",
                    "description": "Remittance notes"
                }
            },
            "required": ["invoice_identifier", "amount"]
        }
    },
    {
        "name": "list_clients",
        "description": "Retrieve all registered enterprise clients with NTN/STRN tax numbers, emails, and address records.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "search": {
                    "type": "STRING",
                    "description": "Search keyword for company or contact name"
                }
            }
        }
    },
    {
        "name": "create_client",
        "description": "Register a new corporate enterprise client into the PayFlow platform.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "company": { "type": "STRING", "description": "Company legal entity name" },
                "name": { "type": "STRING", "description": "Primary contact person" },
                "email": { "type": "STRING", "description": "Corporate billing email" },
                "phone": { "type": "STRING", "description": "Phone number" },
                "tax_id": { "type": "STRING", "description": "NTN or STRN tax registration number" },
                "address": { "type": "STRING", "description": "Registered business address" }
            },
            "required": ["company", "name", "email"]
        }
    },
    {
        "name": "auto_reconcile_overdue",
        "description": "Execute autonomous receivables reconciliation: scans all issued invoices, flags past-due receivables as OVERDUE, calculates aging buckets, and generates follow-up notices.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    }
]

class PayBotEngine:
    """
    Autonomous AI Financial Operations Engine for PayFlow.
    Powered by Gemini 2.5 Flash / 1.5 Flash with Native Function Calling,
    paired with an internal autonomous executor for zero-dependency reliability.
    """

    @staticmethod
    def find_client(db: Session, identifier: str) -> Optional[Client]:
        ident = str(identifier).strip()
        if ident.isdigit():
            c = db.query(Client).filter(Client.id == int(ident)).first()
            if c:
                return c
        c = db.query(Client).filter(Client.company.ilike(f"%{ident}%")).first()
        if c:
            return c
        c = db.query(Client).filter(Client.name.ilike(f"%{ident}%")).first()
        if c:
            return c
        return db.query(Client).filter(Client.email.ilike(f"%{ident}%")).first()

    @staticmethod
    def find_invoice(db: Session, identifier: str) -> Optional[Invoice]:
        ident = str(identifier).strip().upper()
        if ident.isdigit():
            inv = db.query(Invoice).filter(Invoice.id == int(ident)).first()
            if inv:
                return inv
        # Match "INV-2026-0001" or partial "0001"
        inv = db.query(Invoice).filter(Invoice.invoice_number == ident).first()
        if inv:
            return inv
        return db.query(Invoice).filter(Invoice.invoice_number.ilike(f"%{ident}%")).first()

    @staticmethod
    async def execute_tool(
        tool_name: str, 
        args: Dict[str, Any], 
        db: Session, 
        current_user: User
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """
        Executes an agentic tool against the database and microservice bus.
        Returns (result_dict, action_payload).
        """
        action_payload = None

        if tool_name == "get_financial_summary":
            invoices = db.query(Invoice).all()
            total_billed = sum(i.total_amount for i in invoices)
            total_revenue = sum(i.total_amount for i in invoices if i.status == InvoiceStatus.PAID)
            total_outstanding = sum(i.total_amount for i in invoices if i.status in [InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE])
            pra_tax_collected = sum(i.tax_amount for i in invoices if i.status == InvoiceStatus.PAID)
            
            paid_count = sum(1 for i in invoices if i.status == InvoiceStatus.PAID)
            issued_count = sum(1 for i in invoices if i.status == InvoiceStatus.ISSUED)
            overdue_count = sum(1 for i in invoices if i.status == InvoiceStatus.OVERDUE)
            
            collection_rate = round((total_revenue / total_billed * 100) if total_billed > 0 else 0, 1)

            result = {
                "total_invoiced_pkr": round(total_billed, 2),
                "total_settled_pkr": round(total_revenue, 2),
                "outstanding_receivables_pkr": round(total_outstanding, 2),
                "pra_16_tax_collected_pkr": round(pra_tax_collected, 2),
                "collection_efficiency_percent": collection_rate,
                "counts": {
                    "total": len(invoices),
                    "paid": paid_count,
                    "issued": issued_count,
                    "overdue": overdue_count
                }
            }
            return result, None

        elif tool_name == "list_invoices":
            query = db.query(Invoice)
            status_filter = args.get("status")
            if status_filter:
                try:
                    s_enum = InvoiceStatus[status_filter.upper()]
                    query = query.filter(Invoice.status == s_enum)
                except KeyError:
                    pass
            
            client_name = args.get("client_name")
            if client_name:
                query = query.join(Client).filter(
                    (Client.company.ilike(f"%{client_name}%")) | 
                    (Client.name.ilike(f"%{client_name}%"))
                )
            
            limit = int(args.get("limit", 10))
            invoices = query.order_by(Invoice.created_at.desc()).limit(limit).all()

            results = []
            for inv in invoices:
                results.append({
                    "id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "client": inv.client.company if inv.client else "Unknown",
                    "client_contact": inv.client.name if inv.client else "N/A",
                    "total_pkr": inv.total_amount,
                    "status": inv.status.value,
                    "due_date": inv.due_date.strftime("%Y-%m-%d") if inv.due_date else None,
                    "pdf_url": f"/api/v1/invoices/{inv.id}/pdf"
                })
            return {"invoices": results, "total_found": len(results)}, None

        elif tool_name == "get_invoice_details":
            ident = args.get("invoice_identifier", "")
            inv = PayBotEngine.find_invoice(db, ident)
            if not inv:
                return {"error": f"Invoice not found matching '{ident}'"}, None

            items = [{
                "description": it.description,
                "quantity": it.quantity,
                "unit_price": it.unit_price,
                "total": it.total
            } for it in inv.items]

            payments = [{
                "amount": p.amount,
                "method": p.payment_method,
                "reference_no": p.reference_no,
                "date": p.paid_at.strftime("%Y-%m-%d %H:%M") if p.paid_at else None
            } for p in inv.payments]

            return {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "client": {
                    "company": inv.client.company,
                    "name": inv.client.name,
                    "email": inv.client.email,
                    "tax_id": inv.client.tax_id,
                    "address": inv.client.address
                },
                "status": inv.status.value,
                "issue_date": inv.issue_date.strftime("%Y-%m-%d") if inv.issue_date else None,
                "due_date": inv.due_date.strftime("%Y-%m-%d") if inv.due_date else None,
                "currency": inv.currency,
                "subtotal_pkr": inv.subtotal,
                "pra_tax_rate": inv.tax_rate,
                "pra_tax_pkr": inv.tax_amount,
                "total_pkr": inv.total_amount,
                "notes": inv.notes,
                "items": items,
                "payments": payments,
                "pdf_url": f"/api/v1/invoices/{inv.id}/pdf"
            }, None

        elif tool_name == "create_invoice":
            client_ident = args.get("client_identifier", "")
            client = PayBotEngine.find_client(db, client_ident)
            if not client:
                # Default to first client if not found
                client = db.query(Client).first()
                if not client:
                    return {"error": f"No client found matching '{client_ident}' and database has no clients."}, None

            items_input = args.get("items", [])
            if not items_input:
                items_input = [{"description": "Professional IT Services", "quantity": 1, "unit_price": 100000}]

            # Calculate math
            subtotal = sum(float(i.get("quantity", 1)) * float(i.get("unit_price", 0)) for i in items_input)
            tax_rate = 0.16
            tax_amount = round(subtotal * tax_rate, 2)
            total_amount = round(subtotal + tax_amount, 2)
            
            invoice_num = generate_invoice_number(db)
            due_days = int(args.get("due_in_days", 15))
            due_date = datetime.utcnow() + timedelta(days=due_days)

            invoice = Invoice(
                invoice_number=invoice_num,
                client_id=client.id,
                created_by_id=current_user.id,
                status=InvoiceStatus.ISSUED,
                issue_date=datetime.utcnow(),
                due_date=due_date,
                currency="PKR",
                subtotal=round(subtotal, 2),
                tax_rate=tax_rate,
                tax_amount=tax_amount,
                total_amount=total_amount,
                notes=args.get("notes", "Auto-generated by PayBot AI Controller. Payable via RAAST Instant ID 03446751031.")
            )
            db.add(invoice)
            db.commit()
            db.refresh(invoice)

            for item_data in items_input:
                q = float(item_data.get("quantity", 1))
                up = float(item_data.get("unit_price", 0))
                db_item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=item_data.get("description", "Deliverable"),
                    quantity=q,
                    unit_price=up,
                    total=round(q * up, 2)
                )
                db.add(db_item)
            db.commit()

            # Polyglot event dispatch
            await notify_node_worker("INVOICE_CREATED", {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "client_id": client.id,
                "total_amount": invoice.total_amount,
                "created_by": "PayBot AI"
            })

            record_audit_log(
                db, current_user.id, "INVOICE_CREATED_BY_PAYBOT", "INVOICE", str(invoice.id),
                f"PayBot autonomously issued corporate invoice {invoice.invoice_number} for {client.company} (PKR {invoice.total_amount:,.2f})"
            )

            action_payload = {
                "type": "invoice_created",
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "client_company": client.company,
                "total_amount": invoice.total_amount,
                "pdf_url": f"/api/v1/invoices/{invoice.id}/pdf"
            }

            return {
                "success": True,
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "client": client.company,
                "subtotal_pkr": invoice.subtotal,
                "pra_16_tax_pkr": invoice.tax_amount,
                "total_pkr": invoice.total_amount,
                "due_date": invoice.due_date.strftime("%Y-%m-%d"),
                "pdf_url": f"/api/v1/invoices/{invoice.id}/pdf",
                "message": f"Successfully created corporate invoice {invoice.invoice_number} for {client.company}."
            }, action_payload

        elif tool_name == "update_invoice_status":
            ident = args.get("invoice_identifier", "")
            new_status_str = args.get("new_status", "").upper()
            inv = PayBotEngine.find_invoice(db, ident)
            if not inv:
                return {"error": f"Invoice not found matching '{ident}'"}, None

            try:
                target_status = InvoiceStatus[new_status_str]
            except KeyError:
                return {"error": f"Invalid status '{new_status_str}'. Must be PAID, OVERDUE, ISSUED, or CANCELLED."}, None

            old_status = inv.status.value
            inv.status = target_status
            db.commit()

            await notify_node_worker("INVOICE_STATUS_UPDATED", {
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "old_status": old_status,
                "new_status": target_status.value,
                "updated_by": "PayBot AI"
            })

            record_audit_log(
                db, current_user.id, "INVOICE_STATUS_UPDATED_BY_PAYBOT", "INVOICE", str(inv.id),
                f"PayBot updated invoice {inv.invoice_number} status from {old_status} to {target_status.value}"
            )

            action_payload = {
                "type": "status_updated",
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "status": target_status.value
            }

            return {
                "success": True,
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "old_status": old_status,
                "new_status": target_status.value,
                "client": inv.client.company if inv.client else "N/A"
            }, action_payload

        elif tool_name == "record_payment":
            ident = args.get("invoice_identifier", "")
            inv = PayBotEngine.find_invoice(db, ident)
            if not inv:
                return {"error": f"Invoice not found matching '{ident}'"}, None

            amount = float(args.get("amount", inv.total_amount))
            method = args.get("payment_method", "RAAST").upper()
            ref_no = args.get("reference_no") or f"RAAST-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            notes = args.get("notes", "Automated settlement processed by PayBot AI")

            payment = Payment(
                invoice_id=inv.id,
                amount=amount,
                payment_method=method,
                reference_no=ref_no,
                notes=notes,
                paid_at=datetime.utcnow()
            )
            db.add(payment)

            # Auto-reconcile status
            total_paid = sum(p.amount for p in inv.payments) + amount
            if total_paid >= inv.total_amount:
                inv.status = InvoiceStatus.PAID
            db.commit()

            await notify_node_worker("PAYMENT_RECORDED", {
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "amount": amount,
                "status": inv.status.value,
                "payment_id": payment.id
            })

            record_audit_log(
                db, current_user.id, "PAYMENT_RECORDED_BY_PAYBOT", "PAYMENT", str(payment.id),
                f"PayBot recorded payment of PKR {amount:,.2f} via {method} for {inv.invoice_number}. Ledger status: {inv.status.value}"
            )

            action_payload = {
                "type": "payment_recorded",
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "amount": amount,
                "status": inv.status.value
            }

            return {
                "success": True,
                "payment_id": payment.id,
                "invoice_number": inv.invoice_number,
                "amount_paid_pkr": amount,
                "payment_method": method,
                "reference_no": ref_no,
                "invoice_status": inv.status.value
            }, action_payload

        elif tool_name == "list_clients":
            search = args.get("search", "")
            query = db.query(Client)
            if search:
                query = query.filter(
                    (Client.company.ilike(f"%{search}%")) | 
                    (Client.name.ilike(f"%{search}%")) | 
                    (Client.email.ilike(f"%{search}%"))
                )
            clients = query.all()
            return {
                "clients": [{
                    "id": c.id,
                    "company": c.company,
                    "name": c.name,
                    "email": c.email,
                    "phone": c.phone,
                    "tax_id": c.tax_id,
                    "address": c.address,
                    "invoice_count": len(c.invoices)
                } for c in clients]
            }, None

        elif tool_name == "create_client":
            company = args.get("company", "").strip()
            name = args.get("name", "").strip()
            email = args.get("email", "").strip()
            if not company or not name or not email:
                return {"error": "Company, contact name, and email are required to register a client."}, None

            client = Client(
                company=company,
                name=name,
                email=email,
                phone=args.get("phone", "+92-42-111-000-000"),
                tax_id=args.get("tax_id", f"NTN-{datetime.utcnow().strftime('%y%m%d%H')}-0"),
                address=args.get("address", "Lahore, Pakistan")
            )
            db.add(client)
            db.commit()
            db.refresh(client)

            record_audit_log(
                db, current_user.id, "CLIENT_CREATED_BY_PAYBOT", "CLIENT", str(client.id),
                f"PayBot registered new corporate account: {client.company} ({client.name})"
            )

            action_payload = {
                "type": "client_created",
                "client_id": client.id,
                "company": client.company
            }

            return {
                "success": True,
                "client_id": client.id,
                "company": client.company,
                "name": client.name,
                "email": client.email,
                "tax_id": client.tax_id
            }, action_payload

        elif tool_name == "auto_reconcile_overdue":
            now = datetime.utcnow()
            invoices = db.query(Invoice).filter(Invoice.status == InvoiceStatus.ISSUED).all()
            
            flagged = []
            for inv in invoices:
                if inv.due_date and inv.due_date < now:
                    inv.status = InvoiceStatus.OVERDUE
                    flagged.append({
                        "id": inv.id,
                        "invoice_number": inv.invoice_number,
                        "client": inv.client.company if inv.client else "N/A",
                        "total_pkr": inv.total_amount,
                        "overdue_days": (now - inv.due_date).days
                    })
            
            if flagged:
                db.commit()
                record_audit_log(
                    db, current_user.id, "AUTONOMOUS_RECONCILIATION_RUN", "SYSTEM", "BATCH",
                    f"PayBot autonomous sweep identified and updated {len(flagged)} overdue invoices to OVERDUE status."
                )

            # Build aging analysis
            all_overdue = db.query(Invoice).filter(Invoice.status == InvoiceStatus.OVERDUE).all()
            overdue_total = sum(i.total_amount for i in all_overdue)

            action_payload = {
                "type": "reconciliation_completed",
                "flagged_count": len(flagged),
                "total_overdue_pkr": overdue_total
            }

            return {
                "status": "Reconciliation cycle complete",
                "newly_flagged_count": len(flagged),
                "newly_flagged_invoices": flagged,
                "total_overdue_portfolio_pkr": round(overdue_total, 2),
                "reconciliation_advice": "Recommended action: Dispatch automated RAAST settlement reminders to counterparty accounts."
            }, action_payload

        return {"error": f"Unknown tool: {tool_name}"}, None

    @classmethod
    async def chat(
        cls, 
        user_message: str, 
        history: List[Dict[str, str]], 
        db: Session, 
        current_user: User,
        custom_api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Coordinates the conversational AI reasoning loop.
        Prioritizes the Google Gemini API with native function calling.
        Falls back seamlessly to local autonomous rule-execution if no API key is provided.
        """
        api_key = custom_api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        
        # If Gemini API key is available, execute multi-turn function calling with Gemini
        if api_key and api_key.strip():
            try:
                gemini_res = await cls._execute_gemini_turn(
                    user_message=user_message,
                    history=history,
                    api_key=api_key.strip(),
                    db=db,
                    current_user=current_user
                )
                if gemini_res:
                    return gemini_res
            except Exception as e:
                # Log error and fall through to local autonomous execution
                print(f"[PayBot] Gemini API call exception: {e}")

        # Local Autonomous Fallback (Zero external dependency guarantee)
        return await cls._execute_local_autonomous(
            user_message=user_message,
            db=db,
            current_user=current_user,
            has_gemini_key=bool(api_key and api_key.strip())
        )

    @classmethod
    async def _execute_gemini_turn(
        cls, 
        user_message: str, 
        history: List[Dict[str, str]], 
        api_key: str, 
        db: Session, 
        current_user: User
    ) -> Optional[Dict[str, Any]]:
        """
        Sends request to Google Gemini API with functionDeclarations and resolves tool calls.
        """
        model = settings.GEMINI_MODEL or "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        # Construct Gemini message format
        contents = []
        for h in history[-8:]:  # keep recent context
            role = "user" if h.get("role") in ["user", "human"] else "model"
            contents.append({
                "role": role,
                "parts": [{"text": h.get("content", "")}]
            })
        contents.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

        request_body = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "tools": [{
                "functionDeclarations": GEMINI_TOOLS
            }],
            "toolConfig": {
                "functionCallingConfig": {
                    "mode": "AUTO"
                }
            }
        }

        last_action_payload = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Multi-turn tool execution loop (max 4 turns)
            for _ in range(4):
                response = await client.post(url, json=request_body)
                if response.status_code != 200:
                    print(f"[PayBot] Gemini error {response.status_code}: {response.text}")
                    return None

                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return None

                candidate = candidates[0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])

                function_calls = [p["functionCall"] for p in parts if "functionCall" in p]

                if not function_calls:
                    # Model returned final natural language text
                    text_parts = [p["text"] for p in parts if "text" in p]
                    final_text = "\n\n".join(text_parts) if text_parts else "PayBot executed the requested action."
                    return {
                        "response": final_text,
                        "action_taken": last_action_payload,
                        "source": "gemini",
                        "model": model,
                        "suggested_prompts": cls._generate_next_prompts(last_action_payload)
                    }

                # Handle function call
                fn_call = function_calls[0]
                fn_name = fn_call.get("name")
                fn_args = fn_call.get("args", {})

                # Execute tool locally
                tool_result, action_payload = await cls.execute_tool(fn_name, fn_args, db, current_user)
                if action_payload:
                    last_action_payload = action_payload

                # Append assistant functionCall and user/tool functionResponse to contents
                contents.append({
                    "role": "model",
                    "parts": [{"functionCall": {"name": fn_name, "args": fn_args}}]
                })
                contents.append({
                    "role": "function",
                    "parts": [{
                        "functionResponse": {
                            "name": fn_name,
                            "response": {"output": tool_result}
                        }
                    }]
                })
                request_body["contents"] = contents

        return None

    @classmethod
    async def _execute_local_autonomous(
        cls, 
        user_message: str, 
        db: Session, 
        current_user: User,
        has_gemini_key: bool
    ) -> Dict[str, Any]:
        """
        Autonomous intent parser that guarantees full platform automation even
        without an external Gemini API key.
        """
        msg = user_message.lower().strip()
        last_action = None

        # 1. Summary / Financial Overview
        if any(w in msg for w in ["summary", "analytics", "financial", "kpi", "revenue", "how much", "health", "balance"]):
            res, _ = await cls.execute_tool("get_financial_summary", {}, db, current_user)
            text = (
                f"### 📊 PayFlow Executive Financial Summary\n\n"
                f"- **Total Billed:** PKR {res['total_invoiced_pkr']:,.2f}\n"
                f"- **Settled Revenue:** PKR {res['total_settled_pkr']:,.2f}\n"
                f"- **Outstanding Receivables:** PKR {res['outstanding_receivables_pkr']:,.2f}\n"
                f"- **PRA 16% Tax Collected:** PKR {res['pra_16_tax_collected_pkr']:,.2f}\n"
                f"- **Collection Efficiency:** {res['collection_efficiency_percent']}%\n\n"
                f"**Portfolio Counts:** {res['counts']['paid']} Paid • {res['counts']['issued']} Issued • {res['counts']['overdue']} Overdue"
            )
            return {
                "response": text,
                "action_taken": None,
                "source": "local_autonomous",
                "suggested_prompts": [
                    "Auto-reconcile overdue invoices",
                    "Create invoice for Systems Limited",
                    "List all unpaid invoices"
                ]
            }

        # 2. Autonomous Reconciliation / Overdue check
        if any(w in msg for w in ["reconcile", "overdue", "aging", "settle overdue", "sweep"]):
            res, last_action = await cls.execute_tool("auto_reconcile_overdue", {}, db, current_user)
            flagged = res.get("newly_flagged_invoices", [])
            
            if flagged:
                items_md = "\n".join([f"- **{f['invoice_number']}** ({f['client']}): PKR {f['total_pkr']:,.2f} — *{f['overdue_days']} days past maturity*" for f in flagged])
                text = (
                    f"### ⚡ Autonomous Reconciliation Cycle Completed\n\n"
                    f"Identified and transitioned **{len(flagged)} invoices** past due maturity date to `OVERDUE` status:\n\n"
                    f"{items_md}\n\n"
                    f"**Total Overdue Portfolio:** PKR {res['total_overdue_portfolio_pkr']:,.2f}\n\n"
                    f"*All compliance state changes written to the immutable audit ledger.*"
                )
            else:
                text = (
                    f"### ⚡ Autonomous Reconciliation Cycle Completed\n\n"
                    f"All issued receivables are currently within standard maturity terms. Total overdue portfolio: **PKR {res['total_overdue_portfolio_pkr']:,.2f}**."
                )

            return {
                "response": text,
                "action_taken": last_action,
                "source": "local_autonomous",
                "suggested_prompts": [
                    "Show financial summary",
                    "List all invoices",
                    "Create a new invoice"
                ]
            }

        # 3. Create Invoice Intent
        if any(w in msg for w in ["create invoice", "generate invoice", "issue invoice", "bill", "new invoice"]):
            # Extract client name
            client_name = "Systems Limited"
            for c in ["jazz", "systems", "arbisoft", "10pearls"]:
                if c in msg:
                    client_name = c
                    break

            # Extract amount
            amount = 350000.0
            amounts_found = re.findall(r'(\d+[\d,]*)(?:\s*(?:k|thousand|pkr|rs|m|million))?', msg)
            if amounts_found:
                num_str = amounts_found[0].replace(',', '')
                try:
                    num_val = float(num_str)
                    if re.search(r'\b(?:k|thousand)\b', msg) or re.search(r'\d+\s*k\b', msg):
                        num_val *= 1000
                    elif re.search(r'\b(?:million|m)\b', msg) or re.search(r'\d+\s*m\b', msg):
                        num_val *= 1000000
                    if num_val > 100:
                        amount = num_val
                except ValueError:
                    pass

            desc = "Enterprise IT Architecture Consultation & Sprint Deliverables"
            if "for" in msg:
                parts = msg.split("for")
                if len(parts) > 1:
                    desc_candidate = parts[-1].strip().title()
                    if len(desc_candidate) > 5 and not any(w in desc_candidate.lower() for w in ["systems", "jazz", "arbisoft"]):
                        desc = desc_candidate

            res, last_action = await cls.execute_tool(
                "create_invoice",
                {
                    "client_identifier": client_name,
                    "items": [{"description": desc, "quantity": 1, "unit_price": amount}],
                    "due_in_days": 15,
                    "notes": "Generated by PayBot AI Controller. Payable via RAAST Instant ID 03446751031."
                },
                db, current_user
            )

            if "error" in res:
                text = f"❌ Could not create invoice: {res['error']}"
            else:
                text = (
                    f"### ✅ Corporate Tax Invoice Issued: {res['invoice_number']}\n\n"
                    f"- **Client Entity:** {res['client']}\n"
                    f"- **Service Subtotal:** PKR {res['subtotal_pkr']:,.2f}\n"
                    f"- **PRA 16% Sales Tax:** PKR {res['pra_16_tax_pkr']:,.2f}\n"
                    f"- **Net Payable Total:** **PKR {res['total_pkr']:,.2f}**\n"
                    f"- **Due Maturity:** {res['due_date']} (Net 15 terms)\n\n"
                    f"📄 **[View & Stream ReportLab PDF]({res['pdf_url']})**"
                )

            return {
                "response": text,
                "action_taken": last_action,
                "source": "local_autonomous",
                "suggested_prompts": [
                    f"Mark {res.get('invoice_number', 'invoice')} as paid",
                    "Show financial summary",
                    "List all invoices"
                ]
            }

        # 4. Mark Invoice as Paid / Update Status
        if any(w in msg for w in ["mark as paid", "paid", "settle", "settled"]):
            # Extract invoice number or id
            inv_matches = re.findall(r'(?:inv-\d{4}-\d{4}|\binv\b\s*#?\s*\d+|\b\d+\b)', msg)
            target = inv_matches[0] if inv_matches else "1"
            
            res, last_action = await cls.execute_tool(
                "update_invoice_status",
                {"invoice_identifier": target, "new_status": "PAID"},
                db, current_user
            )

            if "error" in res:
                # If specific target failed, try marking the first issued invoice as paid
                first_issued = db.query(Invoice).filter(Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE])).first()
                if first_issued:
                    res, last_action = await cls.execute_tool(
                        "update_invoice_status",
                        {"invoice_identifier": str(first_issued.id), "new_status": "PAID"},
                        db, current_user
                    )
            
            if "error" in res:
                text = f"❌ {res['error']}"
            else:
                text = (
                    f"### 💰 Remittance Confirmed & Ledger Reconciled\n\n"
                    f"- **Invoice Number:** `{res['invoice_number']}`\n"
                    f"- **Client Counterparty:** {res['client']}\n"
                    f"- **Previous State:** `{res['old_status']}` &rarr; **New State:** `PAID`\n"
                    f"- **Audit:** Recorded immutable state change in compliance ledger."
                )

            return {
                "response": text,
                "action_taken": last_action,
                "source": "local_autonomous",
                "suggested_prompts": [
                    "Show financial summary",
                    "Auto-reconcile overdue invoices",
                    "List all invoices"
                ]
            }

        # 5. List Invoices
        if any(w in msg for w in ["list", "invoices", "show invoices", "unpaid", "pending"]):
            status_param = None
            if "unpaid" in msg or "pending" in msg or "issued" in msg:
                status_param = "ISSUED"
            elif "paid" in msg:
                status_param = "PAID"
            elif "overdue" in msg:
                status_param = "OVERDUE"

            res, _ = await cls.execute_tool("list_invoices", {"status": status_param, "limit": 8}, db, current_user)
            invs = res.get("invoices", [])
            if not invs:
                text = "No invoices found matching current criteria."
            else:
                rows = "\n".join([f"| `{i['invoice_number']}` | {i['client']} | PKR {i['total_pkr']:,.2f} | `{i['status']}` | [PDF]({i['pdf_url']}) |" for i in invs])
                text = (
                    f"### 📋 Corporate Invoices Ledger\n\n"
                    f"| Invoice # | Client | Total | Status | Action |\n"
                    f"| :--- | :--- | :--- | :--- | :--- |\n"
                    f"{rows}"
                )

            return {
                "response": text,
                "action_taken": None,
                "source": "local_autonomous",
                "suggested_prompts": [
                    "Auto-reconcile overdue accounts",
                    "Create a new invoice",
                    "Financial overview"
                ]
            }

        # 6. List Clients
        if any(w in msg for w in ["clients", "accounts", "customers", "counterparty"]):
            res, _ = await cls.execute_tool("list_clients", {}, db, current_user)
            clients = res.get("clients", [])
            rows = "\n".join([f"- **{c['company']}** — Contact: {c['name']} (`{c['email']}`) • NTN: `{c['tax_id'] or 'Registered'}`" for c in clients])
            text = (
                f"### 🏢 Registered Enterprise Counterparties\n\n"
                f"{rows}\n\n"
                f"You can instruct PayBot to issue an invoice for any of these corporate clients."
            )
            return {
                "response": text,
                "action_taken": None,
                "source": "local_autonomous",
                "suggested_prompts": [
                    "Create invoice for Jazz Telecom",
                    "Create invoice for Arbisoft",
                    "Show financial summary"
                ]
            }

        # Default Helpful Agent Guidance
        tip = ""
        if not has_gemini_key:
            tip = "\n\n> 💡 *Tip: Add your Gemini API key in PayBot settings or `.env` to unlock open-ended conversational reasoning, custom billing calculations, and multi-turn workflows!*"

        text = (
            f"### 🤖 PayBot Autonomous Operations Assistant\n\n"
            f"I am actively connected to your PayFlow database, ledger, and event worker. Here are some actions I can automate for you right now:\n\n"
            f"- **⚡ Autonomous Reconcile:** *\"Auto-reconcile overdue invoices\"*\n"
            f"- **📄 Instant Invoicing:** *\"Create invoice for Systems Limited for 450,000 PKR for Cloud Engineering\"*\n"
            f"- **💰 Settle Receivables:** *\"Mark invoice INV-2026-0002 as paid\"*\n"
            f"- **📊 Financial KPIs:** *\"Show financial summary and outstanding receivables\"*\n"
            f"- **🏢 Client Registry:** *\"Show all registered corporate clients\"*"
            f"{tip}"
        )
        return {
            "response": text,
            "action_taken": None,
            "source": "local_autonomous",
            "suggested_prompts": [
                "Show financial summary",
                "Auto-reconcile overdue invoices",
                "Create invoice for Systems Limited",
                "List all unpaid invoices"
            ]
        }

    @staticmethod
    def _generate_next_prompts(action_payload: Optional[Dict[str, Any]]) -> List[str]:
        if not action_payload:
            return [
                "Auto-reconcile overdue invoices",
                "Show financial summary",
                "Create invoice for Jazz Telecom",
                "List all unpaid invoices"
            ]
        
        atype = action_payload.get("type")
        if atype == "invoice_created":
            inv_num = action_payload.get("invoice_number", "invoice")
            return [
                f"Mark {inv_num} as paid",
                "Show updated financial summary",
                "Auto-reconcile overdue accounts"
            ]
        elif atype in ["status_updated", "payment_recorded"]:
            return [
                "Show updated financial summary",
                "List all unpaid invoices",
                "Create a new invoice"
            ]
        elif atype == "reconciliation_completed":
            return [
                "Show financial summary",
                "List all invoices",
                "Create a new invoice"
            ]
        return [
            "Show financial summary",
            "Auto-reconcile overdue invoices",
            "Create invoice for Systems Limited"
        ]
