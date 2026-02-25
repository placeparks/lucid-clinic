# CLAUDE.md — Lucid Clinic Inc
## Agentic CRM + Computer Use Platform
### Project Governance, Scope & Development Standards

> **Version:** 1.0  
> **Date:** February 2026  
> **Authors:** Mirac (CTO) × Nick (Clinic Owner)  
> **Status:** Active

---

## 1. PROJECT OVERVIEW

Lucid Clinic Inc is an AI-first practice management platform for chiropractic clinics. It replaces manual, disconnected clinic workflows with an **agentic CRM** that operates existing clinic software (starting with EZBIS) via **Computer Use agents** — no API required, no workflow disruption.

The product is built in two layers:
- **Lucid CRM** — a cloud-based patient intelligence and re-engagement platform
- **Lucid Agent** — a Computer Use agent that interfaces with any clinic software on-site

---

## 2. MISSION STATEMENT

> Enable any chiropractic clinic to run a smarter, more automated practice using AI agents — without changing the software they already know and love.

---

## 3. SCOPE

### 3.1 In Scope

#### Data Layer
- Ingestion and normalization of EZBIS EZMERGE.DAT patient exports
- Postgres database as source of truth for all patient records
- ETL pipeline: parse, clean, deduplicate, and score patient data
- Re-engagement queue generation with priority scoring (0–100)
- Patient tier classification: `active` / `warm` / `cool` / `cold` / `dormant`

#### CRM Layer
- Patient profile management (read/write)
- Re-engagement queue dashboard
- Appointment history and visit tracking
- Insurance and financial data display (read-only)
- Search, filter, and segment by tier, score, city, insurance, visit count
- Clinic owner dashboard: bookings, churn, revenue trends

#### Agent Layer
- Computer Use agent connecting to clinic machine via Tailscale + VNC
- Auto-sync patient data from EZBIS into Postgres (no manual CSV export)
- Agent-driven appointment booking and rescheduling in EZBIS UI
- Agent-driven patient record updates
- Playwright/PyAutoGUI fallback for repetitive deterministic tasks

#### Communication Layer (Phase 2+)
- SMS re-engagement via Twilio
- Email re-engagement via Resend
- Automated appointment reminders
- DNC list enforcement (hard block — never contact flagged numbers)

#### Infrastructure
- DigitalOcean cloud hosting (aligns with existing Claw Club infra)
- Tailscale mesh for secure clinic machine access
- Postgres (primary DB), Redis (queues/caching)
- FastAPI backend, Next.js frontend

---

### 3.2 Out of Scope (Current Phase)

The following are explicitly **not** being built right now. Do not implement, prototype, or design for these without a formal scope change:

- ❌ Native EZBIS API integration (does not exist; use Computer Use instead)
- ❌ Billing / insurance claims processing or submission
- ❌ EHR / clinical notes / SOAP notes (medical records — HIPAA complexity)
- ❌ Payment processing or credit card handling
- ❌ Integration with other clinic software (ChiroTouch, Jane, Kareo) — Phase 3+
- ❌ Mobile app (web-first for now)
- ❌ Multi-tenant agent orchestration (single clinic first — Nick's clinic)
- ❌ AI diagnosis or clinical decision support (out of scope permanently)
- ❌ Voice agents (post-MVP)
- ❌ Any feature that requires modifying EZBIS data directly without agent supervision

---

## 4. ARCHITECTURE

### 4.1 System Layers

```
┌─────────────────────────────────────────────────────────┐
│  LAYER 3 — LUCID CRM CLOUD (DigitalOcean)               │
│  Postgres · FastAPI · Next.js · Redis                   │
│  Patient DB · Re-engagement Queue · Dashboard           │
└───────────────────────┬─────────────────────────────────┘
                        │ Tailscale Mesh (encrypted)
┌───────────────────────▼─────────────────────────────────┐
│  LAYER 2 — LUCID AGENT (Computer Use)                   │
│  Claude Computer Use API · VNC Session Controller       │
│  Task Runner · Playwright Fallback · Screenshot Logger  │
└───────────────────────┬─────────────────────────────────┘
                        │ VNC / RDP
┌───────────────────────▼─────────────────────────────────┐
│  LAYER 1 — CLINIC MACHINE (Nick's Windows Server)       │
│  EZBIS Office · Tailscale · VNC Server                  │
│  Zero workflow changes for clinic staff                 │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Data Flow

```
EZBIS (on-site)
  → Computer Use Agent reads UI / exports data
  → ETL Pipeline (parse, clean, normalize, score)
  → Postgres (source of truth)
  → FastAPI (CRM API)
  → Next.js Dashboard (clinic owner view)
  → Re-engagement Queue → Twilio / Resend (Phase 2)
```

### 4.3 Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Database | Supabase Postgres 17 | Managed, auth + storage included |
| Backend API | FastAPI (Python) | Aligns with ETL codebase |
| Frontend | Next.js 16 (App Router) | Fast, full-stack capable |
| Agent Runtime | Claude Computer Use API | Core differentiator |
| VNC Control | python-vnc / Playwright | Agent interface layer |
| Clinic Tunnel | Tailscale | Already in use, proven |
| SMS | Twilio | Integrated (mock + live) |
| Email | Resend | Integrated (mock + live) |
| Cache/Queue | Redis | Job queues for agent tasks |
| Auth | Supabase Auth | Replaces Clerk, integrated with DB |
| Backend Hosting | Railway | Auto-deploy from GitHub |
| Frontend Hosting | Vercel | Optimized for Next.js |

---

## 5. DATABASE SCHEMA (Canonical)

### 5.1 Core Tables

```sql
-- patients: normalized from EZBIS EZMERGE.DAT
patients (
  id, account_id, account_type,
  first_name, middle_initial, last_name, called_name, suffix,
  sex, marital, birthdate, account_created, last_appt,
  address, city, state, zip,
  cell_phone, alt_phone, work_phone, email,
  is_dnc,               -- HARD FLAG: never contact if true
  pref_contact,
  ins_carrier, ins_plan_type, ins_group, ins_member_id, ins_code,
  balance, pat_balance, total_charges, total_receipts, total_visits, copay,
  ref_by, remarks, employment,
  reengagement_score,   -- 0-100, computed
  tier,                 -- active/warm/cool/cold/dormant
  synced_at,            -- last time agent pulled this record
  created_at, updated_at
)

-- reengagement_queue: actionable outreach list
reengagement_queue (
  id, patient_id, account_id,
  full_name, called_name, cell_phone, email,
  last_appt, days_since_appt,
  tier, score, has_insurance, total_visits,
  city, state,
  status,               -- pending / contacted / responded / booked / dead
  contact_attempts,
  last_contacted_at,
  created_at
)

-- agent_sessions: audit log of all Computer Use activity
agent_sessions (
  id, session_type,     -- sync / book_appointment / update_record
  clinic_id,
  started_at, ended_at,
  status,               -- success / failed / partial
  records_affected,
  screenshots_path,     -- stored for audit
  error_log,
  created_at
)

-- clinics: multi-tenant ready from day 1
clinics (
  id, name, owner_name, owner_email,
  tailscale_node_id,    -- for agent routing
  vnc_host, vnc_port,
  software,             -- ezbis / chirotouch / etc (future)
  timezone,
  active,
  created_at
)
```

---

## 6. SCORING ALGORITHM

Patient re-engagement scores are computed at ETL time and refreshed on every sync.

### 6.1 Score Components (0–100)

| Factor | Points | Logic |
|--------|--------|-------|
| Last appt < 6 months | +40 | Active patient |
| Last appt 6–12 months | +35 | Warm |
| Last appt 1–2 years | +28 | Cool |
| Last appt 2–3 years | +18 | Cold |
| Last appt 3–5 years | +10 | Very cold |
| Last appt 5+ years | +2 | Dormant |
| Has email | +20 | High contact value |
| Has cell phone | +15 | SMS reachable |
| Has alt phone | +5 | Backup contact |
| Visits ≥ 20 | +10 | High value patient |
| Visits ≥ 10 | +7 | Mid value |
| Visits ≥ 5 | +4 | Established |
| Has insurance | +8 | Lower friction to return |
| Is DNC | -30 | Hard penalty |
| No contact info | -15 | Unreachable |

### 6.2 Tier Classification

| Tier | Last Appointment | Priority |
|------|-----------------|----------|
| `active` | < 6 months | Monitor only |
| `warm` | 6–12 months | High — act now |
| `cool` | 1–2 years | High — good ROI |
| `cold` | 2–5 years | Medium — targeted |
| `dormant` | 5+ years | Low — bulk only |

---

## 7. AGENT GOVERNANCE

The Computer Use agent has significant access to clinic systems. These rules are non-negotiable.

### 7.1 Agent Permissions

| Action | Permitted | Notes |
|--------|-----------|-------|
| Read patient records | ✅ Yes | Core sync function |
| Export reports (Survey Generator) | ✅ Yes | Data sync only |
| Book appointments | ✅ Yes | With confirmation step |
| Update patient contact info | ✅ Yes | Logged, reversible |
| Delete patient records | ❌ Never | Hard block |
| Submit insurance claims | ❌ Never | Out of scope |
| Access billing/payment screens | ❌ Never | Out of scope |
| Run batch billing operations | ❌ Never | Out of scope |
| Operate outside EZBIS UI | ❌ Never | Scoped to EZBIS only |

### 7.2 Agent Safety Rules

1. **Every agent session is logged** with timestamps, actions taken, and screenshots
2. **Agent never operates autonomously at scale** without a human-approved task queue
3. **Confirmation required** before any write operation (booking, record update)
4. **DNC flag is a hard block** — agent checks is_dnc before any patient interaction
5. **Agent must detect and halt** if it encounters an unexpected EZBIS screen
6. **Max session duration:** 30 minutes per run — prevents runaway processes
7. **Screenshot every action** — stored for 30-day audit trail
8. **Failsafe:** if agent confidence < threshold, it stops and alerts Mirac

### 7.3 Tailscale Security Rules

- Nick's machine is only accessible via Tailscale — never exposed to public internet
- Agent runs from a dedicated DigitalOcean droplet on the tailnet
- VNC credentials are stored in environment variables, never in code
- Access is revocable by Nick at any time by removing the node from tailnet

---

## 8. HIPAA & DATA COMPLIANCE

Lucid Clinic handles Protected Health Information (PHI). These are standing rules:

1. **No PHI in logs** — strip names, DOB, SSN from all application logs
2. **No PHI in error messages** — use account IDs only in error tracking
3. **Database encrypted at rest** — DigitalOcean managed Postgres with encryption enabled
4. **Transit encrypted** — all connections via TLS 1.2+ / Tailscale WireGuard
5. **No PHI in third-party analytics** — Mixpanel, Sentry, etc. get anonymized data only
6. **Data residency** — patient data stays in US-region servers only
7. **BAA required** — before onboarding any clinic, a Business Associate Agreement must be signed
8. **Retention policy** — raw EZMERGE.DAT files deleted after ETL, not stored long-term
9. **Access control** — clinic owners see only their own patients (row-level security in Postgres)
10. **SMS/email opt-out** — any patient reply of STOP / UNSUBSCRIBE must immediately update is_dnc = true

> ⚠️ **Note:** Lucid Clinic is not yet a covered entity. Until a formal HIPAA compliance review is completed, do not store EHR data (clinical notes, diagnoses, treatment records). Demographic + appointment data only.

---

## 9. DEVELOPMENT PHASES

### Phase 1 — Foundation (Weeks 1–2) ✅ COMPLETE
- [x] EZBIS data analysis and schema mapping
- [x] ETL pipeline (EZMERGE.DAT → SQLite prototype)
- [x] Patient scoring algorithm
- [x] Re-engagement queue generation
- [x] FastAPI backend with patient CRUD endpoints (SQLite — Postgres migration pending)
- [x] Database seeded: 14,721 patients, 6,820 queue items scored & tiered
- [ ] Migrate SQLite → Postgres on DigitalOcean
- [ ] Auth setup with Clerk

### Phase 2 — CRM Dashboard (Weeks 3–5) ✅ COMPLETE
- [x] Next.js dashboard scaffold (App Router + Tailwind CSS v4)
- [x] Patient list view with tier/score filtering, search, pagination
- [x] Re-engagement queue UI with status management
- [x] Patient detail page (contact, demographics, insurance, financial)
- [x] Analytics dashboard: tier breakdown, contact coverage, top queue items

### Phase 3 — Computer Use Agent (Weeks 6–9) ✅ COMPLETE
- [ ] Nick installs Tailscale on clinic server
- [x] VNC session controller (Mock + Live stubs)
- [x] Computer Use agent loop (Claude API + tool handling)
- [x] Agent task: auto-sync (sync_patients — read-only)
- [x] Agent task: appointment booking (with confirmation gate)
- [x] Agent task: patient record update (with confirmation gate)
- [x] Agent session logging and audit UI (screenshots, iterations, results)
- [x] Task governance: DNC hard block, max iterations, max session time

### Phase 4 — Re-engagement Engine (Weeks 10–12) ✅ COMPLETE
- [x] Twilio SMS integration (with mock mode)
- [x] Resend email integration (with mock mode)
- [x] Campaign builder: channel select, tier targeting, message templates
- [x] Campaign send: batch outreach with DNC double-gate
- [x] Message log with delivery status tracking
- [x] Webhook endpoints for Twilio delivery + STOP/UNSUBSCRIBE handling
- [x] Webhook endpoints for Resend delivery + bounce/complaint handling
- [x] Response tracking (replied messages, opt-outs)
- [ ] Booking attribution (manual — update via queue status)

### Phase 5 — Multi-Clinic Scale (Month 4+)
- [ ] Multi-tenant clinic onboarding flow
- [ ] Per-clinic agent configuration
- [ ] Clinic admin portal
- [ ] Billing / subscription (Stripe)

---

## 10. DEFINITION OF DONE

A feature is **done** when:
1. Code is written and tested locally
2. No patient PII in logs or error messages
3. Agent actions are logged with screenshots (agent features only)
4. Deployed to DigitalOcean staging environment
5. Nick has reviewed and signed off (for clinic-facing features)
6. README updated if architecture changes

---

## 11. NAMING CONVENTIONS

| Thing | Convention | Example |
|-------|-----------|---------|
| Database tables | snake_case, plural | `patients`, `agent_sessions` |
| API endpoints | kebab-case, RESTful | `/api/patients/:id/score` |
| Python files | snake_case | `etl_pipeline.py` |
| React components | PascalCase | `PatientCard.tsx` |
| Environment vars | SCREAMING_SNAKE_CASE | `POSTGRES_URL` |
| Branch names | kebab-case with prefix | `feat/agent-sync`, `fix/dnc-check` |
| Agent task names | snake_case verbs | `sync_patients`, `book_appointment` |

---

## 12. ENVIRONMENT VARIABLES (Required)

```bash
# Database
POSTGRES_URL=

# Agent
ANTHROPIC_API_KEY=
VNC_HOST=             # Tailscale IP of clinic machine
VNC_PORT=5900
VNC_PASSWORD=

# Tailscale
TAILSCALE_AUTH_KEY=

# Communications (Phase 2)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
RESEND_API_KEY=

# Auth
CLERK_SECRET_KEY=
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=

# App
NEXT_PUBLIC_APP_URL=
ENVIRONMENT=development  # development / staging / production
```

---

## 13. BOUNDARIES — WHAT WE DO NOT DO

These are standing decisions. Do not revisit without explicit agreement from both Mirac and Nick.

1. **We do not touch EZBIS billing** — insurance claims, ERA posting, collection desk are off limits permanently
2. **We do not store clinical notes** — SOAP notes, diagnoses, treatment data are EHR territory
3. **We do not replace EZBIS** — we augment it. The agent uses EZBIS, not around it
4. **We do not contact DNC patients** — ever, under any circumstances
5. **We do not build for non-chiropractic clinics** — in Phase 1-3, chiro only. Focus matters.
6. **We do not over-engineer** — ship working software. SQLite was fine for day 1. Postgres is fine for year 1.
7. **We do not store raw DAT files** — ETL, load, delete the source file
8. **We do not give the agent write access to EZBIS without a confirmation step** — always human-in-the-loop for writes

---

## 14. CONTACTS & OWNERSHIP

| Role | Person | Responsibility |
|------|--------|---------------|
| CTO / Lead Engineer | Mirac | Architecture, backend, agent development |
| Clinic Owner / Domain Expert | Nick | EZBIS access, clinical validation, user testing |
| AI Platform | Claude (Anthropic) | Development assistance, code generation |

---

*This document is the single source of truth for Lucid Clinic development decisions. When in doubt, refer here first.*
