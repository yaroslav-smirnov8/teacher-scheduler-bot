# AI Teacher Helper

## 🚀 Overview

AI Teacher Helper is a production-oriented Telegram automation system for private teachers and small tutoring studios. It combines lesson scheduling, recurring lesson management, AI-generated interactive homework, payment tracking, reminders, and student/teacher workflows in one async bot application.

The project is designed as an operational assistant, not a simple chatbot: business rules live in services, data integrity is enforced at the database layer, and background jobs automate the repetitive work that normally consumes a teacher's admin time.

## 🎯 Problem

Independent teachers often run their business across disconnected tools: messengers for communication, spreadsheets for payments, calendars for scheduling, and separate AI tools for lesson materials. That creates duplicated work, missed reminders, unclear payment status, and weak visibility into student homework progress.

AI Teacher Helper solves this by turning Telegram into a lightweight command center for the full tutoring workflow.

## 💡 Solution

The system provides role-based Telegram flows for teachers and students, backed by an async service layer and relational data model. Teachers can register students, schedule one-time or recurring lessons, send manual or AI-generated homework, track completion, manage prepaid lesson balances, handle reschedule requests, and rely on background automation for reminders and maintenance.

AI homework generation is provider-agnostic: the app can call NVIDIA NIM, Mistral, or Groq, validate the result with Pydantic schemas, repair malformed JSON, and store both student-readable text and structured interactive exercises.

## ⚙️ Features

- Role-based Telegram bot experience for teachers and students using aiogram routers, filters, FSM states, and middleware.
- One-time and recurring lesson scheduling with conflict checks, database uniqueness constraints, recurrence exceptions, and materialized future lessons.
- Student reschedule workflow with teacher approval/decline actions and notification delivery.
- AI homework generation with multi-provider fallback, strict schema validation, JSON repair flow, manual JSON import, preview, regeneration, and teacher approval before sending.
- Interactive homework engine with multiple exercise types, student attempts, scoring, and teacher-facing progress views.
- Homework lifecycle tracking: sent, received, completed, edited, teacher marks, optional work completion, and historical stats.
- Payment operations for per-lesson status, unpaid/upcoming/recent lesson views, notes, reminders, prepaid lesson deposits, balance application, refunds, forfeits, and transaction history.
- Unified background job runner for lesson reminders, payment reminders, post-lesson homework prompts, daily summaries, recurring lesson materialization, homework cleanup, and rate-limit cleanup.
- Async SQLAlchemy persistence with PostgreSQL defaults, transaction-safe service methods, indexed tables, constraints, and versioned migrations.
- Test coverage for recurrence generation, recurring service behavior, access control, database models, integration flows, and initialization logic.

## 🧠 Architecture

The application is organized around a layered bot architecture:

- **Interface layer:** aiogram routers and handlers expose Telegram workflows for registration, calendar actions, recurring lessons, rescheduling, homework, AI homework, feedback, and payments.
- **Middleware and filters:** database sessions, rate limiting, and teacher/student authorization are applied before business logic executes.
- **Service layer:** lesson, recurrence, payment, homework, feedback, user, notification, and access-control services isolate operational rules from Telegram UI handlers.
- **AI generation layer:** provider adapters implement a common interface, while the generator orchestrates prompt construction, provider fallback, schema validation, repair, and formatting.
- **Persistence layer:** SQLAlchemy models define teachers, students, lessons, recurring patterns, exceptions, reschedule requests, homework, attempts, payment transactions, and feedback.
- **Automation layer:** one background job loop coordinates periodic reminders, summaries, recurring materialization, cleanup, and post-lesson homework prompts.

```mermaid
flowchart TD
    A[Teacher / Student in Telegram] --> B[aiogram Routers and FSM Flows]
    B --> C[Middlewares: DB Session, Rate Limit]
    C --> D[Role Filters: Teacher / Student]
    D --> E[Service Layer]

    E --> F[Lesson and Recurrence Services]
    E --> G[Homework and AI Homework Services]
    E --> H[Payment and Balance Services]
    E --> I[Notification Service]

    G --> J[AI Homework Generator]
    J --> K[Provider Chain: NVIDIA NIM / Mistral / Groq]
    J --> L[Pydantic Schema Validation and JSON Repair]

    F --> M[(PostgreSQL via Async SQLAlchemy)]
    G --> M
    H --> M
    I --> N[Telegram Notifications]

    O[BackgroundJobs Loop] --> F
    O --> G
    O --> H
    O --> I
```

Key technical decisions:

- **Async-first runtime:** aiogram, async SQLAlchemy, and provider calls keep long-running Telegram and AI workflows non-blocking.
- **Service-oriented business logic:** scheduling, payments, homework, access control, and recurrence are testable outside Telegram handlers.
- **Provider abstraction for AI:** generation is not coupled to a single LLM vendor, which improves reliability and cost flexibility.
- **Structured AI output:** generated homework must pass a Pydantic schema before it becomes a student-facing interactive assignment.
- **Database-backed integrity:** constraints, indexes, migrations, and row locking for balance operations protect operational data as usage grows.
- **Single job orchestrator:** periodic work is centralized, easier to reason about, and avoids scattering long-running loops across handlers.

## 🔧 Tech Stack

- **Language:** Python
- **Bot framework:** aiogram 3
- **Database:** PostgreSQL by default, SQLAlchemy asyncio, asyncpg
- **Local/test database:** SQLite with aiosqlite
- **AI providers:** NVIDIA NIM, Mistral, Groq via provider adapters
- **Validation:** Pydantic
- **HTTP client:** httpx
- **Scheduling/automation:** asyncio background jobs
- **Testing:** pytest, pytest-asyncio
- **Configuration:** python-dotenv

## 🧪 Example Usage

1. A teacher registers in Telegram and adds students.
2. The teacher schedules a one-time lesson or creates a recurring weekly, biweekly, or monthly pattern.
3. The system checks conflicts, stores the lesson, and sends relevant notifications.
4. After a lesson, the bot prompts the teacher to assign homework.
5. The teacher generates AI homework by choosing a topic, CEFR level, focus area, and exercise count.
6. The app validates the AI output, previews it for the teacher, and sends it to the student after approval.
7. The student completes interactive exercises, and the teacher can review attempts, marks, and homework history.
8. Payment status and prepaid lesson balances are tracked alongside the teaching workflow.

Minimal local setup:

```bash
pip install -r requirements.txt
```

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/teacherhelper

# Optional AI provider keys
NVIDIA_NIM_API_KEY=your_key
MISTRAL_API_KEY=your_key
GROQ_API_KEY=your_key
```

```bash
python3 -m bot.main
```

Run tests:

```bash
python3 -m pytest
```

## 🎯 Why This Matters

**For startups:** this is the kind of vertical AI workflow product that can start narrow, own a high-friction operational niche, and expand into payments, analytics, CRM, and content generation.

**For AI systems:** the project demonstrates practical LLM integration beyond a prompt demo: provider fallback, structured outputs, schema validation, repair paths, human approval, storage, and downstream interactive use.

**For automation:** the bot removes repeated admin work from scheduling, reminders, homework assignment, completion tracking, and payment follow-up while preserving teacher control at decision points.

## 📈 Possible Extensions

- Add a web dashboard for teachers with analytics, calendar drag-and-drop, payment reporting, and homework performance trends.
- Move background processing to a dedicated worker queue for larger deployments and stronger retry semantics.
- Add multi-teacher organization accounts with staff roles, shared student records, and studio-level reporting.
- Introduce adaptive homework generation based on past attempt history and recurring student mistakes.
- Integrate Stripe, YooKassa, or another payment provider for automated invoicing and reconciliation.
- Add observability with structured logs, metrics, tracing, and admin alerts for provider failures or reminder delivery issues.
- Expand AI provider routing with cost controls, model-specific quality scoring, and cached reusable exercise packs.
- Support richer content types such as files, voice answers, rubric-based speaking practice, and teacher feedback templates.
