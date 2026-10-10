<p align="center">
  <img src="assets/logo.svg" alt="PayFlow Enterprise" width="480" />
</p>

<p align="center">
  <strong>Autonomous Multi-Tenant Invoicing, Receivables &amp; Financial Operations Platform</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285F4?style=flat-square&logo=google&logoColor=white" alt="Gemini AI" />
  <img src="https://img.shields.io/badge/Node.js-18+-339933?style=flat-square&logo=nodedotjs&logoColor=white" alt="Node.js" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React 18" />
  <img src="https://img.shields.io/badge/Vue-3-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white" alt="Vue 3" />
  <img src="https://img.shields.io/badge/Tax_Compliance-PRA_16%25-blue?style=flat-square" alt="PRA 16%" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License" />
</p>

---

## Overview

**PayFlow Pro** is an enterprise-grade multi-tenant invoicing and financial operations platform engineered for modern B2B billing, automated receivables management, and regulatory tax compliance.

The platform is fully automated with **PayBot**, an agentic AI financial controller powered by the **Google Gemini API** with native function calling. PayBot autonomously issues itemized corporate tax invoices, reconciles past-due receivables, calculates Punjab Revenue Authority (PRA 16%) sales tax, records banking remittances, and performs aging sweeps against the live financial ledger.

PayFlow combines a high-performance **Python FastAPI** backend, a zero-dependency **Node.js** background event worker, a modern **React 18** executive administrative dashboard, and a lightweight **Vue 3** counterparty remittance portal.

---

## Architecture

The system implements a polyglot microservice layout separating high-throughput financial REST operations from asynchronous webhook event dispatching and AI reasoning.

```mermaid
flowchart LR
    subgraph UI ["Client Tier"]
        AdminApp["React 18 Executive Ledger\n(:3000 / Modern Terminal)"]
        ClientPortal["Vue 3 Remittance Portal\n(:3000 / Counterparty Desk)"]
    end

    subgraph AI ["Intelligence Tier"]
        PayBot["PayBot AI Controller\n• Google Gemini 2.5 Flash / 1.5 Flash\n• Native Function Calling Tools\n• Local Autonomous Rule Engine Fallback"]
    end

    subgraph CoreServices ["Microservice Engine"]
        API["FastAPI Backend (:8000)\n• REST Ledger & Schema Validation\n• ReportLab PDF Streaming\n• Zero-Trust IAM & Immutable Audit Logs"]
        Worker["Node.js Event Bus (:5001)\n• Asynchronous Webhook Dispatcher\n• Microservice Delivery Bus"]
    end

    subgraph Persistence ["Persistence Tier"]
        DB[("PostgreSQL 16 / SQLite\n• Invoices & Line Items\n• Enterprise Clients & Users\n• Regulatory Audit Records")]
        Cache[("Redis 7 Cache\n• Rate Limits & Pub/Sub")]
    end

    AdminApp -->|REST / PayBot Chat| API
    AdminApp -.->|Tool Execution| PayBot
    PayBot -->|Function Calls & Mutations| API
    ClientPortal -->|Remittance Confirmation| API
    API -->|HTTP Webhook POST| Worker
    API -->|SQLAlchemy 2.0 ORM| DB
    API -->|Session Tokens| Cache
```

### Components

- **Core Backend (`backend/`)**: Python 3.11+ using FastAPI, Pydantic v2, and SQLAlchemy. Handles billing calculations, tax algorithms, ReportLab PDF streaming, and cryptographic token verification.
- **PayBot Autonomous Controller (`backend/app/services/paybot_service.py`)**: Dual-mode conversational AI engine integrating Google Gemini function calling with direct database tools (`create_invoice`, `update_invoice_status`, `record_payment`, `auto_reconcile_overdue`, `get_financial_summary`).
- **Event Worker (`worker-service/`)**: Zero-dependency Node.js HTTP service listening on port `5001`. Ingests polyglot webhook events asynchronously from FastAPI.
- **Administrative Ledger (`frontend/index.html`)**: React 18 single-page application modeled after high-density modern financial terminals (Linear/Stripe aesthetic), featuring receivables aging, status filters, PayBot AI chat console, and interactive PDF inspection.
- **Client Remittance Portal (`client-portal-vue/index.html`)**: Lightweight Vue 3 interface for corporate counterparty invoice verification, itemized line breakdowns, and RAAST Instant ID / IBFT bank remittance acknowledgment.

---

## Key Platform Capabilities

### 1. PayBot — Autonomous AI Financial Controller
- **Google Gemini API Function Calling**: Connects directly to `gemini-2.5-flash` or `gemini-1.5-flash` using native tool declarations. Gemini autonomously interprets user intent, calls ledger functions, and returns executive explanations.
- **Autonomous Receivables Sweeps**: 1-Click or scheduled sweep that inspects all open receivables, detects invoices past their maturity date, transitions them to `OVERDUE`, recomputes portfolio risk, and drafts remittance notices.
- **Resilient Dual-Mode Execution**: When a Gemini API key is configured, PayBot leverages multi-turn LLM reasoning. If no key is set or offline, PayBot falls back to an internal autonomous rule executor with zero downtime.
- **Live UI State Synchronization**: Any action executed by PayBot (creating an invoice, recording a payment, updating statuses) automatically refreshes the live invoices table, stats deck, and audit log.

### 2. Automated Tax & Compliance Engine (PRA 16%)
- Computes line-item totals, applicable sales tax (**Punjab Revenue Authority PRA 16% on services**), and net payable balances with floating-point precision guards.
- Formats amounts in Pakistani Rupee (PKR) and foreign currencies with clean thousand separators.

### 3. Corporate Tax Invoice Generation (ReportLab)
- Dynamic PDF generation via ReportLab streaming directly over HTTP with `Content-Disposition: inline` for immediate browser preview.
- Incorporates registered NTN, STRN, line-item breakdowns, Punjab Revenue Authority compliance metadata, and banking remittance instructions:
  - **Habib Bank Limited (HBL) IBAN**: `PK72HABB0001234567890123`
  - **RAAST Instant ID**: `03446751031`

### 4. Immutable Compliance Audit Trail
- Every state mutation (invoice issuance, status transition, payment confirmation, AI action) writes an immutable record to the `audit_logs` table.
- Accessible through the administrative compliance tab and REST endpoint `GET /api/v1/audit/`.

### 5. Zero-Trust Identity & Access Management (IAM)
- OAuth2 Bearer tokens with JWT signatures (`HS256`).
- Corporate self-registration is strictly disabled by policy; enterprise users and client counterparties are provisioned exclusively by administration.
- Supports pre-linked corporate Single Sign-On (SSO) authentication for Google Workspace (Gmail) and Microsoft 365 (Outlook / Hotmail).

---

## Project Structure

```
payflow-invoicing-platform/
├── assets/
│   ├── logo.svg               # Vector brand banner
│   ├── icon.svg               # Standalone mark
│   └── logo.png               # High-res rendered banner
├── backend/
│   ├── app/
│   │   ├── models/            # SQLAlchemy database entities (Invoice, Client, Payment, User, AuditLog)
│   │   ├── schemas/           # Pydantic v2 validation models
│   │   ├── routers/           # API routes (auth, invoices, clients, analytics, audit, paybot)
│   │   │   └── paybot.py      # PayBot AI endpoints (chat, status, reconcile, config)
│   │   ├── services/          # Business logic & engines
│   │   │   ├── auth_service.py      # JWT authentication & audit recorder
│   │   │   ├── invoice_service.py   # ReportLab PDF generator & math calculations
│   │   │   └── paybot_service.py    # PayBot Gemini tool execution & autonomous fallback
│   │   ├── config.py          # Environment settings (DB, JWT, Gemini API key)
│   │   ├── database.py        # SQLAlchemy session & engine setup
│   │   └── main.py            # FastAPI factory, CORS & router registration
│   ├── seed_data.py           # Database seeder with realistic Pakistani corporate accounts
│   ├── requirements.txt       # Python dependencies
│   ├── tests/                 # Automated pytest test suite
│   │   ├── conftest.py        # Shared test fixtures & in-memory test database
│   │   ├── test_api.py        # Auth & invoice API tests
│   │   └── test_paybot.py     # PayBot AI tool calling & chat tests
│   └── Dockerfile
├── frontend/
│   ├── index.html             # React 18 administrative ledger & PayBot terminal
│   ├── assets/                # App icons and SVG assets
│   ├── client-portal-vue -> ../client-portal-vue  # Symlink for unified static serving
│   └── Dockerfile
├── client-portal-vue/
│   └── index.html             # Vue 3 counterparty remittance interface
├── worker-service/
│   ├── server.js              # Node.js event bus microservice (:5001)
│   └── Dockerfile
├── docker-compose.yml         # Multi-container orchestration definition
├── start.sh                   # One-command boot script
└── README.md
```

---

## Quickstart

### Option 1: One-Command Boot Script (Recommended)

Run all services simultaneously with the automated boot script:

```bash
git clone https://github.com/hamzaihsan9/payflow-invoicing-platform.git
cd payflow-invoicing-platform

./start.sh
```

Service endpoints:
- **Operations Dashboard**: [http://localhost:3000](http://localhost:3000)
- **FastAPI API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Node.js Event Worker**: [http://localhost:5001/health](http://localhost:5001/health)
- **Counterparty Portal**: [http://localhost:3000/client-portal-vue/index.html](http://localhost:3000/client-portal-vue/index.html)

---

### Option 2: Docker Compose

Run the full polyglot stack in isolated containers (PostgreSQL 16, Redis 7, FastAPI, Node.js Worker, React Nginx):

```bash
docker compose up -d --build
```

---

### Option 3: Manual Local Development

#### 1. Backend Service (FastAPI)

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Seed corporate test accounts (Systems Ltd, Jazz Telecom, Arbisoft, 10Pearls)
python seed_data.py

# Start development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Node.js Event Worker

```bash
cd worker-service
node server.js
```

#### 3. Administrative Dashboard

Serve the frontend using Python's static HTTP server:

```bash
cd frontend
python3 -m http.server 3000
```

---

## PayBot AI Commands Guide

PayBot accepts conversational instructions directly from the **🤖 PAYBOT AI** tab or the floating drawer on any page:

| Intent | Example User Prompt | Action Executed by PayBot |
| :--- | :--- | :--- |
| **Issue Invoice** | *"Create an invoice for Jazz Telecom for 600,000 PKR for 5G Core Architecture Audit"* | Matches client, creates line item, computes 16% PRA tax, generates invoice `INV-2026-XXXX`, writes audit log, returns inline PDF link |
| **Sweep Overdue** | *"Auto-reconcile overdue invoices and analyze aging"* | Scans all issued invoices, flags past-maturity accounts to `OVERDUE`, recomputes portfolio total |
| **Settle Payment** | *"Mark invoice INV-2026-0004 as paid"* | Transitions status to `PAID`, notifies event worker, logs compliance entry |
| **Financial Health** | *"Show me our financial summary and outstanding receivables"* | Aggregates billed revenue, collected amount, PRA tax collected, and collection efficiency percentage |
| **Client Audit** | *"List all registered corporate clients and their tax IDs"* | Queries clients with NTN/STRN, contact persons, and total invoice count |

---

## API Reference

The interactive OpenAPI / Swagger UI documentation is available at `http://localhost:8000/docs`.

### Primary Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/paybot/chat` | Primary conversational AI automation endpoint powered by Google Gemini |
| `GET` | `/api/v1/paybot/status` | PayBot operational health, registered tools, and model configuration |
| `POST` | `/api/v1/paybot/reconcile` | 1-Click autonomous receivables sweep and risk analysis |
| `POST` | `/api/v1/paybot/config` | Runtime Gemini API key and model update |
| `GET` | `/api/v1/invoices/` | List all invoices with optional client and status filters |
| `POST` | `/api/v1/invoices/` | Create a new invoice and dispatch webhook event |
| `GET` | `/api/v1/invoices/{id}` | Retrieve itemized invoice details |
| `GET` | `/api/v1/invoices/{id}/pdf` | Stream ReportLab corporate tax invoice PDF inline |
| `PATCH` | `/api/v1/invoices/{id}/status` | Update invoice status (`PAID`, `OVERDUE`, `ISSUED`, `CANCELLED`) |
| `POST` | `/api/v1/invoices/{id}/payments` | Record payment transaction and recompute ledger |
| `GET` | `/api/v1/clients/` | List registered corporate clients and tax identifiers |
| `POST` | `/api/v1/clients/` | Register new corporate client entity |
| `GET` | `/api/v1/analytics/summary` | Financial KPI aggregates (total billed, settled, outstanding) |
| `GET` | `/api/v1/audit/` | Retrieve chronological compliance audit trail |
| `POST` | `/api/v1/auth/login-json` | Corporate JSON password authentication |
| `POST` | `/api/v1/auth/oauth/sso` | Corporate Single Sign-On (SSO) with policy checks |

### Example Request: Generate Invoice PDF

```bash
curl -I http://localhost:8000/api/v1/invoices/1/pdf
```

Response:
```http
HTTP/1.1 200 OK
content-type: application/pdf
content-disposition: inline; filename="INV-2026-0001.pdf"
content-length: 3558
```

---

## Configuration & Environment Variables

Create a `.env` file in the project root or configure environment variables:

```env
# Database Configuration (Defaults to SQLite for instant local execution)
DATABASE_URL=sqlite:///backend/payflow.db
# For PostgreSQL in Docker:
# DATABASE_URL=postgresql://payflow_user:payflow_secret_2026@localhost:5432/payflow_db

# Security & Tokens
SECRET_KEY=super-secret-enterprise-jwt-key-for-pakistan-it-industry-2026
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Microservices
NODE_WORKER_URL=http://localhost:5001

# Google Gemini AI Configuration
GEMINI_API_KEY=AIzaSyYourGeminiApiKeyHere
GEMINI_MODEL=gemini-2.5-flash
```

*(Note: If `GEMINI_API_KEY` is omitted, PayBot operates seamlessly in Local Autonomous Mode).*

---

## Authentication & RBAC

The API uses OAuth2 Bearer tokens with JWT signatures. For local exploration and dashboard testing, unauthenticated requests automatically resolve to the pre-seeded administrator profile (`admin@payflow.pk` / `hamza@payflow.pk`).

| Role | Permitted Actions |
| :--- | :--- |
| `ADMIN` | Full administrative privileges, audit log inspection, user management |
| `FINANCE_MANAGER` | Create and issue invoices, update payment statuses, manage client profiles |
| `AUDITOR` | Read-only inspection of invoices, analytics summaries, and audit trail |
| `CLIENT` | Counterparty self-service inspection and payment confirmation |

---

## Testing

Run the automated test suite with pytest:

```bash
cd backend
PYTHONPATH=".:$PYTHONPATH" pytest tests/ -v
```

Test coverage includes:
- System health diagnostics (`/health`)
- Precision tax math calculations (`calculate_invoice_totals`)
- Corporate user registration & authentication (`/auth/register`, `/auth/login`)
- PayBot status & registered tool schema validation (`/paybot/status`)
- PayBot conversational financial summary synthesis (`/paybot/chat`)
- PayBot autonomous invoice issuance & math checks
- PayBot remittance reconciliation & status transitions
- PayBot batch overdue sweeps (`/paybot/reconcile`)
- PayBot runtime configuration updates (`/paybot/config`)

---

## Author

**Hamza Ihsan**  
Full-Stack & Systems Engineer — Lahore, Pakistan  
- GitHub: [@hamzaihsan9](https://github.com/hamzaihsan9)  
- LinkedIn: [hamza-ihsan-engineer](https://linkedin.com/in/hamza-ihsan-engineer)

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
