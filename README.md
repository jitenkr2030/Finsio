# Finsio — Financial Operations Platform

Finsio is an internal financial operations platform that consolidates payment processing, invoicing, and double-entry accounting into a single back-office system. It exposes a secure REST API consumed by a React dashboard, giving finance teams real-time visibility into all monetary activity across the business.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Payment Providers](#payment-providers)
- [Accounting & Ledger](#accounting--ledger)
- [Background Tasks](#background-tasks)
- [Deployment](#deployment)

---

## Overview

Finsio is built around three core domains:

| Domain | Responsibility |
|---|---|
| **Payments** | Prepare, process, and track payments across multiple providers (Stripe, PayPal, Braintree, Authorize.net) |
| **Invoicing** | Generate and manage customer invoices with line items, tax, and automatic payment links |
| **Accounting** | Full double-entry ledger via django-ledger — balance sheet, P&L, journal entries, and reconciliation |

All three domains are backed by a Django REST API protected by an internal bearer token and surfaced through a React + Vite dashboard.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   React Frontend                     │
│         (Vite · React 19 · Tailwind v4)              │
│         Port 5000  ──  /api proxy ──►                │
└─────────────────────────────────────────────────────┘
                          │
                   Bearer Token Auth
                          │
┌─────────────────────────────────────────────────────┐
│                  Django REST API                     │
│              (DRF · django-filters)                  │
│                    Port 8000                         │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Payments │  │Invoicing │  │   Accounting      │   │
│  │  App     │  │  App     │  │ (django-ledger)   │   │
│  └──────────┘  └──────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
   ┌──────────┐   ┌──────────────┐  ┌──────────┐
   │PostgreSQL│   │  Celery +    │  │  Redis   │
   │    DB    │   │  Beat Tasks  │  │  Broker  │
   └──────────┘   └──────────────┘  └──────────┘
```

The frontend and backend are developed and served as separate processes. Vite proxies all `/api` requests to Django in development so there are no CORS issues and a single origin is presented to the browser.

---

## Tech Stack

### Backend
| Component | Technology |
|---|---|
| Framework | Django 5.1 + Django REST Framework |
| Database | PostgreSQL (via `dj-database-url` + `psycopg2`) |
| Payments | `django-payments` + `python-getpaid-core` |
| Accounting | `django-ledger` (double-entry bookkeeping) |
| Task Queue | Celery 5 + Redis broker |
| Task Scheduling | `django-celery-beat` |
| Auth | Internal bearer token (`InternalTokenAuthentication`) |
| Exports | Beancount 3 plain-text accounting export |
| Observability | Sentry SDK |
| Runtime | Python 3.12 / Gunicorn |

### Frontend
| Component | Technology |
|---|---|
| Framework | React 19 + TypeScript |
| Build Tool | Vite 8 |
| Routing | React Router v7 |
| Data Fetching | TanStack Query v5 |
| HTTP Client | Axios |
| Styling | Tailwind CSS v4 (CSS-first config) |
| Charts | Recharts |
| Icons | Lucide React |

---

## Features

### Payments
- Multi-provider payment routing (Stripe, PayPal, Braintree, Authorize.net)
- Payment lifecycle management: `NEW → PREPARED → IN_PROGRESS → PAID / FAILED / REFUNDED`
- Idempotency key support to prevent duplicate charges
- Customer and invoice linkage on each payment record
- Searchable and filterable payments table in the dashboard

### Invoicing
- Invoice generation with line items, subtotal, tax, and totals
- Due date tracking and amount-due calculation
- Invoice status workflow: `DRAFT → ISSUED → PAID / VOID`
- Optional linkage to a double-entry journal entry on payment

### Accounting
- Full double-entry bookkeeping via django-ledger
- Balance sheet, profit & loss, and journal entry views
- Ledger account management with account types and balances
- On-demand reconciliation via dashboard button
- Beancount plain-text export for external accountants

### Dashboard
- Real-time overview: total revenue, payment count, pending invoices, system health
- Revenue trend chart
- Recent payments feed
- Per-page filterable tables for all data types

### System Health
- Live health endpoint (`/api/v1/health/`) with per-component status
- Database and Redis connectivity checks
- Auto-refreshes every 5 seconds in the dashboard

---

## Project Structure

```
finsio/
├── backend/                        # Django application
│   ├── apps/
│   │   ├── core/                   # Auth, entities, health check, middleware
│   │   ├── payments/               # Payment model, API, processors, tasks
│   │   ├── invoicing/              # Invoice model, API, line items
│   │   └── accounting/             # Ledger integration, journal entries, reconciliation
│   ├── finsio/
│   │   ├── settings/
│   │   │   ├── base.py             # Shared settings
│   │   │   ├── development.py      # Dev overrides (PostgreSQL, verbose logging)
│   │   │   └── production.py       # Production hardening
│   │   ├── urls.py                 # Root URL config
│   │   └── wsgi.py
│   ├── export_beancount.py         # Beancount export utility
│   ├── seed_data.py                # Development data seeder
│   ├── pyproject.toml              # Python dependencies and tooling config
│   └── manage.py
│
├── frontend/                       # React + Vite application
│   ├── src/
│   │   ├── components/
│   │   │   └── Layout.tsx          # Sidebar navigation shell
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx       # Overview stats, chart, recent payments
│   │   │   ├── Payments.tsx        # Payments list with filter/search
│   │   │   ├── Invoices.tsx        # Invoice list
│   │   │   ├── Accounting.tsx      # Tabbed ledger views
│   │   │   └── Health.tsx          # Live system health monitor
│   │   ├── lib/
│   │   │   └── api.ts              # Axios client + all API functions
│   │   ├── App.tsx                 # Router + QueryClient setup
│   │   ├── main.tsx
│   │   └── index.css               # Tailwind v4 + design tokens
│   ├── vite.config.ts              # Dev server + /api proxy config
│   └── package.json
│
├── start.sh                        # Starts both servers concurrently
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 14+
- Redis 7+ (for Celery; optional in development — health shows "degraded" without it)

### 1. Clone and install backend dependencies

```bash
cd backend
pip install -e ".[dev]"
```

### 2. Set environment variables

Copy the example and fill in your values:

```bash
cp .env.example .env
```

See [Environment Variables](#environment-variables) for all required keys.

### 3. Run database migrations

```bash
cd backend
DJANGO_SETTINGS_MODULE=finsio.settings.development python manage.py migrate
```

### 4. Install frontend dependencies

```bash
cd frontend
npm install
```

### 5. Start both servers

```bash
bash start.sh
```

This runs:
- Django API on `http://localhost:8000`
- React dev server on `http://localhost:5000`

Open `http://localhost:5000` in your browser. All `/api` requests are proxied to Django automatically.

### Seed development data (optional)

```bash
cd backend
python seed_data.py
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `DJANGO_SECRET_KEY` | Yes | insecure dev key | Django secret key — must be changed in production |
| `DJANGO_SETTINGS_MODULE` | Yes | — | e.g. `finsio.settings.development` |
| `BACKEND_INTERNAL_TOKEN` | Yes | `change-me-in-production` | Bearer token shared between frontend and Django API |
| `CELERY_BROKER_URL` | No | `redis://localhost:6379/1` | Redis URL for Celery task broker |
| `STRIPE_SECRET_KEY` | No | — | Stripe secret key for payment processing |
| `STRIPE_WEBHOOK_SECRET` | No | — | Stripe webhook signing secret |
| `PAYPAL_CLIENT_ID` | No | — | PayPal REST API client ID |
| `PAYPAL_CLIENT_SECRET` | No | — | PayPal REST API secret |
| `PAYPAL_MODE` | No | `sandbox` | `sandbox` or `live` |
| `BRAINTREE_MERCHANT_ID` | No | — | Braintree merchant ID |
| `BRAINTREE_PUBLIC_KEY` | No | — | Braintree public key |
| `BRAINTREE_PRIVATE_KEY` | No | — | Braintree private key |
| `PAYMENT_HOST` | No | `localhost:8000` | Hostname used in payment callback URLs |

---

## API Reference

All endpoints are prefixed with `/api/v1/` and require the header:

```
Authorization: Bearer <BACKEND_INTERNAL_TOKEN>
```

### Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health/` | System health (database + Redis). Returns `200` when healthy, `503` when degraded — always includes a JSON body. |

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-05-18T23:00:00+00:00",
  "database": "ok",
  "redis": "ok"
}
```

### Payments

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/payments/` | List all payments (paginated, filterable by status/processor) |
| `POST` | `/api/v1/payments/prepare` | Prepare a new payment intent |
| `GET` | `/api/v1/payments/:id` | Retrieve a single payment |
| `GET` | `/api/v1/payments/processors` | List available payment processors |

### Invoicing

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/invoicing/invoices` | List invoices (paginated) |
| `POST` | `/api/v1/invoicing/invoices` | Create a new invoice |
| `GET` | `/api/v1/invoicing/invoices/:id` | Retrieve invoice with line items |

### Accounting

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/accounting/balance-sheet` | Balance sheet for an entity (`?entity=<slug>`) |
| `GET` | `/api/v1/accounting/profit-loss` | Profit & loss report (`?entity=<slug>`) |
| `GET` | `/api/v1/accounting/journal-entries` | Paginated journal entries |
| `GET` | `/api/v1/accounting/ledger-accounts` | Chart of accounts |
| `POST` | `/api/v1/accounting/reconciliation` | Trigger an async reconciliation run |

### Entities

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/entities/` | List all active business entities |
| `POST` | `/api/v1/entities/create` | Create a new entity |
| `GET` | `/api/v1/entities/:slug` | Retrieve entity by slug |

---

## Payment Providers

Finsio supports four payment processors through a unified interface. Each processor is registered as a `getpaid` entry point:

| Processor | Entry Point Key | Notes |
|---|---|---|
| **Stripe** | `finsio-stripe` | Webhook verification via `STRIPE_WEBHOOK_SECRET` |
| **PayPal** | `finsio-paypal` | Sandbox mode configurable via `PAYPAL_MODE` |
| **Braintree** | `finsio-braintree` | Supports cards and PayPal via Braintree vault |
| **Authorize.net** | `finsio-authorize-net` | AIM API integration |

To add a new processor, implement the `BaseProcessor` interface in `apps/payments/processors/` and register it in `pyproject.toml` under `[project.entry-points."getpaid.processors"]`.

---

## Accounting & Ledger

Finsio uses **django-ledger** for all accounting operations. This provides a full double-entry bookkeeping system where every financial event (payment received, invoice issued, refund processed) posts balanced journal entries automatically.

### Key concepts

- **Entity** — a business entity (company, division) that owns a chart of accounts and ledger
- **Journal Entry (JE)** — a balanced set of debits and credits recording a financial event
- **Ledger Account** — a node in the chart of accounts (assets, liabilities, equity, revenue, expenses)

### Beancount export

For external accounting software or audit purposes, ledger data can be exported to Beancount plain-text format:

```bash
cd backend
python export_beancount.py --entity <slug> --output ledger.beancount
```

---

## Background Tasks

Celery workers handle long-running and scheduled operations. Tasks are routed to dedicated queues per domain:

| Queue | Tasks |
|---|---|
| `payments` | Payment status polling, webhook processing, retry logic |
| `accounting` | Reconciliation runs, journal entry posting |
| `invoicing` | Invoice PDF generation, overdue detection, payment reminders |

### Starting workers

```bash
# Start all workers
celery -A finsio worker -Q payments,accounting,invoicing --loglevel=info

# Start the scheduler (for periodic tasks)
celery -A finsio beat --loglevel=info
```

---

## Deployment

### Production checklist

- Set `DJANGO_SETTINGS_MODULE=finsio.settings.production`
- Set a strong, random `DJANGO_SECRET_KEY`
- Set a strong, random `BACKEND_INTERNAL_TOKEN`
- Set `DATABASE_URL` to a managed PostgreSQL instance
- Set `CELERY_BROKER_URL` to a managed Redis instance
- Run `python manage.py collectstatic` before starting the server
- Build the frontend: `cd frontend && npm run build`

### Production server

```bash
cd backend
gunicorn --bind 0.0.0.0:8000 --workers 4 finsio.wsgi:application
```

### Frontend (static)

After `npm run build`, serve the `frontend/dist/` directory from a CDN or configure Django to serve it via `WhiteNoise`. All routes must fall back to `index.html` for client-side routing to work.

---

## Development Notes

- **Linting** — Ruff is configured for Python (PEP 8, isort, flake8-bugbear rules). Run with `ruff check .`
- **Type checking** — Mypy with django-stubs. Run with `mypy .`
- **Testing** — Pytest with `pytest-django`. Run with `pytest` from the `backend/` directory
- **SQL logging** — Enabled in development settings; all queries are printed to the console
- **Debug toolbar** — Auto-enabled in development if `django-debug-toolbar` is installed
