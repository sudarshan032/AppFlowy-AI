# CLAUDE.md — AppFlowy AI Master Init File

> **Purpose**: This file is the single source of truth for every development session on the AppFlowy AI project. Read this file at the start of every task. It contains the project architecture, development guidelines, feature roadmap, Docker workflow, testing strategy, and implementation plans for building a comprehensive Notion AI clone.

---

## TABLE OF CONTENTS

1. [Project Overview](#1-project-overview)
2. [Architecture & Tech Stack](#2-architecture--tech-stack)
3. [Directory Structure](#3-directory-structure)
4. [Current State — What Is Already Built](#4-current-state--what-is-already-built)
5. [Development Guidelines (MUST FOLLOW)](#5-development-guidelines-must-follow)
6. [Docker Workflow](#6-docker-workflow)
7. [Testing Strategy](#7-testing-strategy)
8. [Git Workflow](#8-git-workflow)
9. [Feature Roadmap — Full Notion AI Clone](#9-feature-roadmap--full-notion-ai-clone)
10. [Implementation Plans by Phase](#10-implementation-plans-by-phase)
11. [API Contracts & Interfaces](#11-api-contracts--interfaces)
12. [LLM Provider Architecture](#12-llm-provider-architecture)
13. [Database Schema Reference](#13-database-schema-reference)
14. [Key File Paths](#14-key-file-paths)
15. [Environment Variables](#15-environment-variables)
16. [Troubleshooting & Common Issues](#16-troubleshooting--common-issues)

---

## 1. PROJECT OVERVIEW

**AppFlowy AI** is a local-first, privacy-preserving Notion AI clone. The goal is to replicate and extend every Notion AI capability within the AppFlowy ecosystem, running entirely in Docker containers.

**Core Principles:**
- **Local-First**: All AI processing can run locally via Ollama (no data leaves the machine)
- **Privacy-Preserving**: No user data sent to external APIs unless explicitly configured
- **Modular Plugin Architecture**: Every feature is a swappable plugin/module
- **Docker-Native**: Everything runs in Docker. Every change must be Docker-tested
- **Comprehensive Testing**: 90%+ test coverage. Unit, integration, e2e, and litmus tests for every module

---

## 2. ARCHITECTURE & TECH STACK

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DOCKER COMPOSE STACK                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐    │
│  │  frontend-   │   │  backend-    │   │     ai-service       │    │
│  │  service     │   │  service     │   │  (Python/FastAPI)    │    │
│  │  (Flutter    │   │  (FastAPI    │   │                      │    │
│  │   Web)       │◄──►  Orchestr.)  │◄──►  - Writing AI       │    │
│  │  Port: 80    │   │  Port: 8000  │   │  - Database AI      │    │
│  └──────────────┘   └──────┬───────┘   │  - Q&A Engine       │    │
│                            │           │  - Agent System      │    │
│                            │           │  - Meeting Notes     │    │
│                     ┌──────▼───────┐   │  - Connectors        │    │
│                     │  PostgreSQL  │   │  Port: 8001          │    │
│                     │  (Primary    │   └──────────┬───────────┘    │
│                     │   Database)  │              │                 │
│                     │  Port: 5432  │   ┌──────────▼───────────┐    │
│                     └──────────────┘   │   Qdrant Vector DB   │    │
│                                        │   Port: 6333          │    │
│                     ┌──────────────┐   └──────────────────────┘    │
│                     │   Ollama     │                                │
│                     │  (Local LLM) │   ┌──────────────────────┐    │
│                     │  Port: 11434 │   │      Redis            │    │
│                     └──────────────┘   │  (Cache/Queue)        │    │
│                                        │  Port: 6379           │    │
│                     ┌──────────────┐   └──────────────────────┘    │
│                     │   Minio      │                                │
│                     │  (Object     │   ┌──────────────────────┐    │
│                     │   Storage)   │   │   Celery Worker       │    │
│                     │  Port: 9000  │   │  (Async Tasks)        │    │
│                     └──────────────┘   └──────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Flutter/Dart (Web build) | Desktop & web UI |
| **Backend API** | Python 3.11+ / FastAPI | REST API orchestration |
| **AI Service** | Python / FastAPI + LangChain | AI capabilities engine |
| **Primary DB** | PostgreSQL 15 | Structured data storage |
| **Vector DB** | Qdrant | Embeddings & semantic search |
| **Cache/Queue** | Redis | Caching, task queue, sessions |
| **Task Queue** | Celery | Async/background AI tasks |
| **LLM (Local)** | Ollama (gpt-oss:20b, llama3, mistral) | Local AI inference |
| **LLM (Cloud)** | OpenAI / Anthropic / Google | Optional cloud AI providers |
| **Embeddings** | nomic-embed-text (768-dim) | Text embeddings for search |
| **Object Storage** | MinIO | File/image storage |
| **Containerization** | Docker + Docker Compose | Everything runs in Docker |
| **CI/CD** | GitHub Actions | Automated testing & deployment |
| **Core Engine** | Rust (AppFlowy Core) | CRDT-based local-first sync |

---

## 3. DIRECTORY STRUCTURE

```
APPFlowy-notion Clone/
├── CLAUDE.md                          # THIS FILE — master reference
├── README.md                          # Project overview
├── docker-compose.yml                 # Docker stack definition
├── docker-compose.override.yml        # Local development overrides
├── .env                               # Root environment variables
├── .env.example                       # Environment template
├── .claude/                           # Claude Code configuration
│   └── settings.local.json            # Bash permissions
│
├── agent/                             # AI Backend Service
│   ├── Dockerfile                     # AI service container
│   ├── requirements.txt               # Python dependencies
│   ├── .env                           # AI service env config
│   ├── alembic.ini                    # DB migration config
│   ├── orchestrator/                  # Main API orchestrator
│   │   ├── main.py                    # FastAPI entry (port 8000)
│   │   ├── llm.py                     # LLM service abstraction
│   │   ├── logic.py                   # Business logic (AgentLogic)
│   │   ├── embeddings.py             # Embedding service
│   │   ├── projection.py             # Markdown output layer
│   │   ├── context_resolver.py       # Page context detection
│   │   └── tools.py                   # LangChain tools
│   ├── ai_plugin/                     # Modular AI Plugin System
│   │   ├── api/
│   │   │   ├── app.py                # Plugin FastAPI app (port 8001)
│   │   │   └── routes/               # Feature-specific routes
│   │   │       ├── writing.py        # Writing AI endpoints
│   │   │       ├── database.py       # Database AI endpoints
│   │   │       ├── agents.py         # Agent endpoints
│   │   │       ├── qa.py             # Q&A endpoints
│   │   │       ├── meeting.py        # Meeting notes endpoints [NEW]
│   │   │       ├── connectors.py     # External connectors [NEW]
│   │   │       ├── translation.py    # Translation endpoints [NEW]
│   │   │       └── sites.py          # Sites/web AI endpoints [NEW]
│   │   ├── capabilities/             # AI capability modules
│   │   │   ├── writing.py            # Writing AI (summarize, improve, etc.)
│   │   │   ├── database_ai.py       # Database autofill & AI properties
│   │   │   ├── agents.py            # Agent orchestration
│   │   │   ├── workspace_qa.py      # Q&A over workspace
│   │   │   ├── meeting_notes.py     # Meeting transcription & notes [NEW]
│   │   │   ├── connectors.py        # External app connectors [NEW]
│   │   │   ├── translation.py       # Multi-language translation [NEW]
│   │   │   ├── image_gen.py         # Image generation [NEW]
│   │   │   └── sites_ai.py          # Sites/SEO AI [NEW]
│   │   ├── providers/                # LLM provider abstraction
│   │   │   ├── base.py              # Abstract AIProvider interface
│   │   │   ├── ollama_provider.py   # Ollama (local)
│   │   │   ├── openai_provider.py   # OpenAI
│   │   │   ├── anthropic_provider.py # Anthropic/Claude
│   │   │   ├── google_provider.py   # Google/Gemini [NEW]
│   │   │   └── config.py            # Provider configuration
│   │   └── core/
│   │       └── engine.py            # Central AI Engine
│   ├── db/                           # Database layer
│   │   ├── database.py              # SQLAlchemy engine
│   │   ├── models.py                # ORM models
│   │   ├── service.py               # CRUD operations
│   │   └── vector_store.py          # Qdrant vector operations
│   ├── templates/                    # Pre-built database templates
│   │   └── definitions.py           # CRM, Tracker, Journal, etc.
│   ├── tests/                        # Test suite
│   │   ├── litmus_unit_test.py      # Unit tests
│   │   ├── litmus_api_test.py       # API tests
│   │   ├── litmus_e2e_test.py       # End-to-end tests
│   │   ├── unit/                    # Granular unit tests
│   │   ├── integration/             # Integration tests
│   │   └── e2e/                     # End-to-end tests
│   ├── migrations/                   # Alembic migrations
│   └── utils/                        # Shared utilities
│
├── appflowy/                          # AppFlowy Core (Rust + Flutter)
│   ├── frontend/
│   │   ├── appflowy_flutter/        # Flutter app
│   │   │   ├── lib/
│   │   │   │   ├── main.dart
│   │   │   │   ├── ai/             # AI integration layer
│   │   │   │   │   ├── ai_agent_client.dart
│   │   │   │   │   ├── ai.dart
│   │   │   │   │   └── ai_plugin_service.dart
│   │   │   │   └── services/
│   │   │   ├── pubspec.yaml
│   │   │   └── test/
│   │   └── rust-lib/                # Rust backend bindings
│   └── doc/                         # Documentation
│
├── agent_qdrant_db/                  # Qdrant persistence volume
├── scripts/                          # DevOps scripts
│   ├── litmus_test.sh               # Full litmus test runner
│   ├── docker_build.sh              # Docker build helper
│   └── seed_data.sh                 # Database seeding
├── start.sh                          # Local dev startup
└── run_appflowy_ai.sh               # AI service startup
```

**Note**: Files marked `[NEW]` are to be created as part of the feature roadmap implementation.

---

## 4. CURRENT STATE — WHAT IS ALREADY BUILT

### ✅ Implemented Features

| Feature | Status | Location |
|---------|--------|----------|
| **AI Chat Integration** | ✅ Complete | `agent/orchestrator/main.py` |
| **Database Creation via NLP** | ✅ Complete | `agent/orchestrator/logic.py` |
| **Property Type Detection** | ✅ Complete | `agent/orchestrator/logic.py` |
| **Record CRUD Operations** | ✅ Complete | `agent/db/service.py` |
| **Semantic Search (Qdrant)** | ✅ Complete | `agent/db/vector_store.py` |
| **Writing: Summarize** | ✅ Complete | `agent/ai_plugin/capabilities/writing.py` |
| **Writing: Improve Writing** | ✅ Complete | `agent/ai_plugin/capabilities/writing.py` |
| **Writing: Fix Grammar** | ✅ Complete | `agent/ai_plugin/capabilities/writing.py` |
| **Writing: Change Tone** | ✅ Complete | `agent/ai_plugin/capabilities/writing.py` |
| **Writing: Translate** | ✅ Complete | `agent/ai_plugin/capabilities/writing.py` |
| **Writing: Make Longer/Shorter** | ✅ Complete | `agent/ai_plugin/capabilities/writing.py` |
| **Writing: Explain** | ✅ Complete | `agent/ai_plugin/capabilities/writing.py` |
| **Writing: Continue Writing** | ✅ Complete | `agent/ai_plugin/capabilities/writing.py` |
| **Database Templates** | ✅ Complete | `agent/templates/definitions.py` |
| **Markdown Projection** | ✅ Complete | `agent/orchestrator/projection.py` |
| **LLM: Ollama Provider** | ✅ Complete | `agent/ai_plugin/providers/ollama_provider.py` |
| **LLM: OpenAI Provider** | ✅ Complete | `agent/ai_plugin/providers/openai_provider.py` |
| **LLM: Anthropic Provider** | ✅ Complete | `agent/ai_plugin/providers/anthropic_provider.py` |
| **Fast-Path Optimization** | ✅ Complete | `agent/orchestrator/main.py` |
| **Unit Tests** | ✅ Complete | `agent/tests/` |
| **Flutter AI Client** | ✅ Complete | `appflowy/frontend/appflowy_flutter/lib/ai/` |

### ❌ NOT YET Implemented (To Build)

| Feature | Priority | Phase |
|---------|----------|-------|
| Docker Compose full stack | 🔴 Critical | Phase 1 |
| PostgreSQL migration (from SQLite) | 🔴 Critical | Phase 1 |
| AI Q&A over workspace | 🟡 High | Phase 2 |
| Database AI Autofill Properties | 🟡 High | Phase 2 |
| AI Summary Properties | 🟡 High | Phase 2 |
| AI Custom Autofill Properties | 🟡 High | Phase 2 |
| Meeting Notes & Transcription | 🟡 High | Phase 3 |
| AI Agents (Autonomous) | 🟡 High | Phase 4 |
| External Connectors (Slack, GDrive) | 🟠 Medium | Phase 5 |
| AI Formula Generation | 🟠 Medium | Phase 3 |
| Image Generation | 🟠 Medium | Phase 4 |
| Notion Sites AI (SEO, web) | 🟢 Low | Phase 6 |
| AI Mail Integration | 🟢 Low | Phase 6 |
| Custom Agent Builder | 🟢 Low | Phase 6 |
| Multi-Model Selection UI | 🟠 Medium | Phase 3 |
| Google/Gemini Provider | 🟠 Medium | Phase 3 |
| AI Usage Analytics | 🟢 Low | Phase 6 |
| Mobile AI Notes | 🟢 Low | Phase 7 |

---

## 5. DEVELOPMENT GUIDELINES (MUST FOLLOW)

> **CRITICAL**: These rules are non-negotiable. Read and follow for every task.

### 5.1 High-Level Architecture Classes
- Every module must be a separate class or component
- Implement a base class/interface for each module type (database, API, auth, AI provider)
- Technology-specific classes implement these interfaces with platform-specific logic
- Example: `AIProvider` (base) → `OllamaProvider`, `OpenAIProvider`, `AnthropicProvider`

### 5.2 Modular Plugin System
- Every feature/service is a plugin that interacts with the architecture interface
- Swapping modules (e.g., changing databases) only updates the module-specific class
- Core architecture must never change when adding/removing plugins

### 5.3 Code Validation with Tests
- **EVERY** code snippet or feature must have:
  - Unit tests
  - Integration tests
  - Ingestion tests (where applicable)
  - Litmus tests (stress tests, edge cases)
- Tests are automated and run at every stage
- **90%+ test coverage** minimum per module

### 5.4 Test Coverage & Monitoring
- If a module's test coverage falls below 90%, flag it for immediate review
- Module-specific tests must be included in the CI/CD pipeline

### 5.5 Docker Update (AFTER EVERY CHANGE)
- **(a) Update Docker**: Ensure `docker-compose.yml`, `Dockerfile`s, and `.env` reflect changes
- **(b) Build**: Rebuild so stop/start preserves features:
  ```bash
  # Backend/AI services:
  docker compose build backend-service ai-service

  # Frontend (Flutter web build first):
  cd frontend && flutter build web --release --dart-define=API_BASE_URL=http://localhost:8000
  cd .. && docker compose build frontend-service

  # Or build everything:
  docker compose build
  ```
- **(c) Docker Test**: Start stack, run tests inside containers:
  ```bash
  docker compose up -d
  docker compose exec backend-service pytest tests/ -v
  ./litmus_test.sh
  ```
- **NEVER commit without Docker build + Docker test passing**

### 5.6 Error Handling & Rollback
- Implement proper error handling for every module
- Fallback logic ensures system continues if one module fails
- No single module failure should break the entire system

### 5.7 Documentation
- Document every module interface
- Explain how modules interact with core system
- Provide clear instructions for adding/swapping/modifying modules

### 5.8 Scalability & Maintainability
- Design every feature with horizontal scaling in mind
- Keep code modular for easy technology migrations
- Clean, readable, well-commented code

---

## 6. DOCKER WORKFLOW

### 6.1 Docker Compose Services

```yaml
# Target docker-compose.yml structure
services:
  frontend-service:     # Flutter web app (nginx)
  backend-service:      # FastAPI orchestrator
  ai-service:           # AI plugin service
  postgres:             # PostgreSQL database
  qdrant:               # Vector database
  redis:                # Cache & task queue
  ollama:               # Local LLM server
  celery-worker:        # Async task processing
  minio:                # Object storage (files, images)
```

### 6.2 Build Commands

```bash
# Full stack build
docker compose build

# Individual service rebuild
docker compose build ai-service
docker compose build backend-service
docker compose build frontend-service

# Start stack
docker compose up -d

# Stop stack (data persists)
docker compose down

# Full reset (destroys volumes)
docker compose down -v

# View logs
docker compose logs -f ai-service
docker compose logs -f backend-service

# Run tests in container
docker compose exec ai-service pytest tests/ -v
docker compose exec backend-service pytest tests/ -v
```

### 6.3 Docker Development Cycle

```
1. Write code
2. Write tests (unit + integration)
3. Run tests locally (quick validation)
4. Update docker-compose.yml / Dockerfile if needed
5. docker compose build <service>
6. docker compose up -d
7. docker compose exec <service> pytest tests/ -v
8. Run litmus_test.sh
9. If all pass → git commit
10. If fail → fix and repeat from step 1
```

---

## 7. TESTING STRATEGY

### 7.1 Test Types

| Type | Purpose | Location | Runner |
|------|---------|----------|--------|
| **Unit** | Individual functions/classes | `agent/tests/unit/` | `pytest` |
| **Integration** | Module interactions | `agent/tests/integration/` | `pytest` |
| **API** | Endpoint validation | `agent/tests/litmus_api_test.py` | `pytest` |
| **E2E** | Full workflow testing | `agent/tests/litmus_e2e_test.py` | `pytest` |
| **Litmus** | Stress/edge cases | `agent/tests/litmus_unit_test.py` | `pytest` |
| **Docker** | In-container testing | Inside containers | `docker compose exec` |
| **Flutter** | Frontend testing | `appflowy/frontend/appflowy_flutter/test/` | `flutter test` |

### 7.2 Test File Naming Convention

```
test_{module_name}.py           # Unit tests
test_{module_name}_integration.py  # Integration tests
test_{module_name}_e2e.py       # End-to-end tests
litmus_{module_name}_test.py    # Litmus/stress tests
```

### 7.3 Test Coverage Requirements

- Every new feature: minimum 90% coverage
- Every new API endpoint: test happy path + error paths + edge cases
- Every new AI capability: test with mock LLM responses
- Every database change: migration test + rollback test

---

## 8. GIT WORKFLOW

```bash
# Before any commit:
# 1. All tests pass
# 2. Docker build succeeds
# 3. Docker tests pass

# Commit format:
git add .
git commit -m "[PHASE-X][FEATURE] Descriptive message explaining why

- What changed
- What it affects
- Test coverage details"
git push

# Branch naming:
# feature/phase-1-docker-setup
# feature/phase-2-workspace-qa
# fix/database-autofill-edge-case
# test/meeting-notes-coverage
```

---

## 9. FEATURE ROADMAP — FULL NOTION AI CLONE

### PHASE 1: Docker Infrastructure & Foundation (Priority: 🔴 CRITICAL)

**Goal**: Containerize the entire stack. Migrate from SQLite to PostgreSQL. Set up Redis, Qdrant, and Ollama in Docker.

| # | Feature | Description | Estimated Effort |
|---|---------|-------------|-----------------|
| 1.1 | Docker Compose Stack | Create full `docker-compose.yml` with all services | 1-2 days |
| 1.2 | Backend Dockerfile | Containerize FastAPI backend with all dependencies | 0.5 day |
| 1.3 | AI Service Dockerfile | Containerize AI plugin service | 0.5 day |
| 1.4 | Frontend Dockerfile | Flutter web build + nginx container | 0.5 day |
| 1.5 | PostgreSQL Migration | Migrate from SQLite to PostgreSQL (Alembic) | 1-2 days |
| 1.6 | Qdrant in Docker | Persist vector DB in Docker volume | 0.5 day |
| 1.7 | Redis Setup | Add Redis for caching and task queuing | 0.5 day |
| 1.8 | Ollama in Docker | Local LLM in container with GPU passthrough | 0.5 day |
| 1.9 | Environment Configuration | `.env` files, secrets management | 0.5 day |
| 1.10 | Health Checks | Health check endpoints for all services | 0.5 day |
| 1.11 | Docker Test Suite | Tests that run inside containers | 1 day |

**Acceptance Criteria**: `docker compose up -d` starts the entire stack. All existing features work. All tests pass inside containers.

---

### PHASE 2: AI Q&A & Enhanced Database AI (Priority: 🟡 HIGH)

**Goal**: Implement workspace-wide Q&A search and intelligent database autofill properties.

| # | Feature | Description | Estimated Effort |
|---|---------|-------------|-----------------|
| 2.1 | Workspace Indexing | Index all pages/databases into Qdrant for Q&A | 2-3 days |
| 2.2 | Q&A Engine | Natural language Q&A over workspace with source citations | 3-4 days |
| 2.3 | AI Summary Property | Auto-summarize page content in database property | 1-2 days |
| 2.4 | AI Key Info Property | Extract key data points from pages | 1-2 days |
| 2.5 | AI Translation Property | Auto-translate content in database columns | 1 day |
| 2.6 | Custom Autofill Property | User-defined AI prompts for database columns | 2-3 days |
| 2.7 | Batch Autofill | Apply autofill across entire database columns | 1-2 days |
| 2.8 | Auto-Update on Edit | Properties auto-update when source content changes | 1-2 days |
| 2.9 | Permission-Aware Search | Q&A respects user permissions | 1-2 days |

**Acceptance Criteria**: Users can ask natural language questions and get answers with citations. Database properties auto-populate with AI-generated content.

---

### PHASE 3: Advanced Writing, Formulas & Multi-Model (Priority: 🟡 HIGH)

**Goal**: Enhance writing capabilities, add AI formula generation, implement multi-model support.

| # | Feature | Description | Estimated Effort |
|---|---------|-------------|-----------------|
| 3.1 | AI Blocks (Inline) | Dedicated AI blocks in editor (summary, action items, custom) | 2-3 days |
| 3.2 | Slash Command System | `/ai`, `/summary`, `/translate`, `/brainstorm`, `/outline` | 2-3 days |
| 3.3 | Highlight-to-AI | Select text → Ask AI for transformation | 1-2 days |
| 3.4 | AI Brainstorm | Generate ideas, talking points, concept lists | 1 day |
| 3.5 | AI Outline Generator | Create structured outlines from notes | 1 day |
| 3.6 | AI Formula Generation | Natural language to database formulas | 2-3 days |
| 3.7 | Formula Explanation | Explain existing formulas in plain English | 1 day |
| 3.8 | Formula Debugging | Debug and fix formula errors with AI | 1-2 days |
| 3.9 | Google/Gemini Provider | Add Google AI as LLM provider | 1-2 days |
| 3.10 | Multi-Model Selection | UI for choosing AI model per request | 1-2 days |
| 3.11 | Auto Model Selection | System picks optimal model per task type | 1-2 days |
| 3.12 | Content Templates | AI-powered content templates (blog, email, social, etc.) | 2 days |

**Acceptance Criteria**: Users can use slash commands, inline AI blocks, and choose between multiple AI models. Formula generation works from plain English.

---

### PHASE 4: AI Agents & Autonomous Operations (Priority: 🟡 HIGH)

**Goal**: Build autonomous AI agents that can perform multi-step operations across the workspace.

| # | Feature | Description | Estimated Effort |
|---|---------|-------------|-----------------|
| 4.1 | Agent Framework | Core agent execution engine with task planning | 3-4 days |
| 4.2 | Multi-Page Operations | Agents work across multiple pages simultaneously | 2-3 days |
| 4.3 | Agent Instructions | Custom instruction pages that guide agent behavior | 1-2 days |
| 4.4 | Agent Memory | Persistent memory bank for agent context | 2-3 days |
| 4.5 | Agent Permissions | Fine-grained permission control for agent actions | 1-2 days |
| 4.6 | Scheduled Agents | Run agents on custom schedules (cron-like) | 2-3 days |
| 4.7 | Trigger-Based Agents | Fire agents on workspace events | 2-3 days |
| 4.8 | Agent Templates | Pre-built agent templates for common tasks | 1-2 days |
| 4.9 | Agent Progress Tracking | UI for viewing agent execution status | 1-2 days |
| 4.10 | Image Generation | DALL-E/Stable Diffusion integration for image creation | 2-3 days |
| 4.11 | Agent Report Generation | Auto-generate summaries of agent work | 1-2 days |

**Acceptance Criteria**: Agents can autonomously create pages, build databases, search workspace, and execute multi-step workflows. Scheduled execution works.

---

### PHASE 5: External Connectors & Integrations (Priority: 🟠 MEDIUM)

**Goal**: Connect external data sources for unified AI search and operations.

| # | Feature | Description | Estimated Effort |
|---|---------|-------------|-----------------|
| 5.1 | Connector Framework | Base connector interface with indexing pipeline | 2-3 days |
| 5.2 | Slack Connector | Index Slack channels, search messages via Q&A | 3-4 days |
| 5.3 | Google Drive Connector | Index Google Docs/Sheets/Slides | 3-4 days |
| 5.4 | GitHub Connector | Index repositories, issues, PRs | 2-3 days |
| 5.5 | Email Connector (IMAP) | Index emails for Q&A search | 2-3 days |
| 5.6 | Jira Connector | Index Jira issues and projects | 2-3 days |
| 5.7 | Unified Search | Single query across all connectors + workspace | 2-3 days |
| 5.8 | Source Citations | Show which connector/source provided the answer | 1-2 days |
| 5.9 | Permission Mapping | Respect connector-specific access controls | 1-2 days |
| 5.10 | Incremental Indexing | Efficient re-indexing (only new/changed content) | 2-3 days |
| 5.11 | MCP Server | Model Context Protocol server for external AI tools | 2-3 days |

**Acceptance Criteria**: Users can search across workspace + Slack + Google Drive + GitHub in a single query. Results include source citations.

---

### PHASE 6: Meeting Notes, Sites AI & Advanced Features (Priority: 🟠 MEDIUM)

**Goal**: Implement meeting transcription, Notion Sites AI, email integration, and analytics.

| # | Feature | Description | Estimated Effort |
|---|---------|-------------|-----------------|
| 6.1 | Audio Transcription Service | Real-time audio-to-text (Whisper-based) | 3-4 days |
| 6.2 | Meeting Notes Block | `/meet` command for meeting recording + notes | 2-3 days |
| 6.3 | Auto-Summarize Meetings | Generate meeting summaries from transcripts | 1-2 days |
| 6.4 | Action Item Extraction | Auto-extract action items from transcripts | 1-2 days |
| 6.5 | Speaker Detection | Detect speaker changes in transcription | 2-3 days |
| 6.6 | Sites AI: SEO | Generate SEO titles, descriptions, meta tags | 1-2 days |
| 6.7 | Sites AI: Content Draft | AI-generated page/blog content for sites | 1-2 days |
| 6.8 | Sites AI: Copy Variations | Generate multiple content versions | 1 day |
| 6.9 | AI Mail: Auto-Labeling | AI-categorize incoming emails | 2-3 days |
| 6.10 | AI Mail: Draft Assist | AI-powered email drafting | 1-2 days |
| 6.11 | AI Usage Analytics | Track AI feature usage, adoption metrics | 2-3 days |
| 6.12 | Custom Agent Builder UI | Drag-and-drop agent configuration | 3-4 days |
| 6.13 | AI Automations | Create triggers + actions with AI assistance | 2-3 days |

**Acceptance Criteria**: Meeting transcription works with auto-summary. Sites have AI-powered SEO. Email integration functional.

---

### PHASE 7: Mobile, Polish & Enterprise Features (Priority: 🟢 LOW)

**Goal**: Mobile AI support, enterprise features, and final polish.

| # | Feature | Description | Estimated Effort |
|---|---------|-------------|-----------------|
| 7.1 | Mobile AI Notes | Background recording on mobile | 3-4 days |
| 7.2 | Mobile Agent | Full agent capabilities on phone | 2-3 days |
| 7.3 | Enterprise Admin Controls | AI usage policies, team management | 2-3 days |
| 7.4 | Audit Logging | Track all AI operations for compliance | 1-2 days |
| 7.5 | Rate Limiting & Quotas | Per-user AI usage limits | 1-2 days |
| 7.6 | Performance Optimization | Caching, batch processing, response streaming | 3-4 days |
| 7.7 | Accessibility | WCAG compliance for AI features | 2-3 days |
| 7.8 | Internationalization | UI support for multiple languages | 2-3 days |
| 7.9 | API Documentation | OpenAPI/Swagger docs for all endpoints | 1-2 days |
| 7.10 | Load Testing | Stress test the entire system under load | 1-2 days |

---

## 10. IMPLEMENTATION PLANS BY PHASE

### PHASE 1 IMPLEMENTATION: Docker Infrastructure

#### Step 1.1: Create `docker-compose.yml`

```yaml
# Target structure — implement this
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: appflowy_ai
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:6333/healthz"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  backend-service:
    build:
      context: .
      dockerfile: agent/Dockerfile.backend
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/appflowy_ai
      - QDRANT_URL=http://qdrant:6333
      - REDIS_URL=redis://redis:6379
      - OLLAMA_BASE_URL=http://ollama:11434
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_healthy
      redis:
        condition: service_healthy

  ai-service:
    build:
      context: .
      dockerfile: agent/Dockerfile.ai
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/appflowy_ai
      - QDRANT_URL=http://qdrant:6333
      - REDIS_URL=redis://redis:6379
      - OLLAMA_BASE_URL=http://ollama:11434
    ports:
      - "8001:8001"
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_healthy

  frontend-service:
    build:
      context: .
      dockerfile: appflowy/frontend/Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend-service
      - ai-service

  celery-worker:
    build:
      context: .
      dockerfile: agent/Dockerfile.ai
    command: celery -A agent.tasks worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/appflowy_ai
      - REDIS_URL=redis://redis:6379
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on:
      - redis
      - postgres

volumes:
  postgres_data:
  qdrant_data:
  redis_data:
  ollama_data:
```

#### Step 1.2: PostgreSQL Migration Strategy

```
1. Create new Alembic migration for PostgreSQL
2. Update db/database.py to use PostgreSQL connection string
3. Update all SQLAlchemy models (replace SQLite-specific types)
4. Create migration script: SQLite → PostgreSQL data transfer
5. Update vector_store.py to use Docker Qdrant URL
6. Test all CRUD operations against PostgreSQL
7. Verify semantic search against Docker Qdrant
```

#### Step 1.3: Dockerfile Templates

**Backend Dockerfile** (`agent/Dockerfile.backend`):
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent/ ./agent/
EXPOSE 8000
CMD ["uvicorn", "agent.orchestrator.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**AI Service Dockerfile** (`agent/Dockerfile.ai`):
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent/ ./agent/
EXPOSE 8001
CMD ["uvicorn", "agent.ai_plugin.api.app:app", "--host", "0.0.0.0", "--port", "8001"]
```

**Frontend Dockerfile** (`appflowy/frontend/Dockerfile`):
```dockerfile
FROM nginx:alpine
COPY appflowy/frontend/appflowy_flutter/build/web /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

---

### PHASE 2 IMPLEMENTATION: Q&A & Database AI

#### Q&A Engine Architecture

```
User Question
    │
    ▼
┌─────────────────────┐
│  Q&A API Endpoint    │  POST /ai/qa/ask
└──────────┬──────────┘
           │
    ┌──────▼──────┐
    │  Embed      │  Convert question to vector
    │  Question   │  using nomic-embed-text
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Vector     │  Search Qdrant for top-K
    │  Search     │  relevant chunks
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Context    │  Build context from retrieved
    │  Assembly   │  chunks with source metadata
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  LLM        │  Generate answer using context
    │  Generation │  + question + system prompt
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Response   │  Answer + source citations
    │  + Citations│  [page_title, page_id, chunk]
    └─────────────┘
```

#### AI Database Property Types

```python
# New property types to implement:
class AIPropertyType(Enum):
    SUMMARY = "ai_summary"          # Auto-summarize page content
    KEY_INFO = "ai_key_info"        # Extract key data points
    TRANSLATION = "ai_translation"  # Auto-translate content
    CUSTOM = "ai_custom"            # User-defined AI prompt

# Each AI property has:
# - source_properties: list of input property names
# - prompt_template: the AI prompt (for CUSTOM type)
# - target_language: for TRANSLATION type
# - auto_update: bool (update on page edit, 5-min delay)
```

---

## 11. API CONTRACTS & INTERFACES

### Base AI Provider Interface

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, List, Dict

class AIProvider(ABC):
    """Base interface all LLM providers must implement."""

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None,
                       temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """Generate text completion."""
        pass

    @abstractmethod
    async def stream(self, prompt: str, system_prompt: Optional[str] = None,
                     temperature: float = 0.7) -> AsyncIterator[str]:
        """Stream text completion token by token."""
        pass

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available."""
        pass
```

### Connector Interface

```python
class BaseConnector(ABC):
    """Interface all external connectors must implement."""

    @abstractmethod
    async def authenticate(self, credentials: Dict) -> bool:
        pass

    @abstractmethod
    async def index(self) -> int:
        """Index all content. Returns count of indexed items."""
        pass

    @abstractmethod
    async def incremental_index(self, since: datetime) -> int:
        """Index only new/changed content since timestamp."""
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        pass

    @abstractmethod
    async def get_source_url(self, item_id: str) -> str:
        """Get link back to original source."""
        pass
```

### Agent Interface

```python
class BaseAgent(ABC):
    """Interface for autonomous AI agents."""

    @abstractmethod
    async def plan(self, task: str) -> List[AgentStep]:
        """Create execution plan for the task."""
        pass

    @abstractmethod
    async def execute_step(self, step: AgentStep) -> StepResult:
        """Execute a single step in the plan."""
        pass

    @abstractmethod
    async def run(self, task: str, max_steps: int = 50,
                  timeout_minutes: int = 20) -> AgentResult:
        """Execute the full task autonomously."""
        pass

    @abstractmethod
    async def get_status(self) -> AgentStatus:
        """Get current execution status."""
        pass
```

---

## 12. LLM PROVIDER ARCHITECTURE

### Provider Registry

```python
# Provider selection logic:
PROVIDERS = {
    "ollama": OllamaProvider,       # Local, free, private
    "openai": OpenAIProvider,       # GPT-4, GPT-3.5
    "anthropic": AnthropicProvider, # Claude models
    "google": GoogleProvider,       # Gemini models
}

# Auto-selection rules:
TASK_MODEL_MAP = {
    "summarize": "ollama",          # Simple tasks → local
    "translate": "ollama",          # Simple tasks → local
    "code_gen": "anthropic",        # Complex tasks → cloud
    "agent_planning": "openai",     # Reasoning → cloud
    "embedding": "ollama",          # Always local
    "formula_gen": "openai",        # Precision → cloud
    "q_and_a": "ollama",           # RAG → local is fine
}
```

### Model Configuration

```python
AVAILABLE_MODELS = {
    "ollama": ["gpt-oss:20b", "llama3:8b", "mistral:7b", "codellama:13b"],
    "openai": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
    "google": ["gemini-pro", "gemini-ultra"],
}
```

---

## 13. DATABASE SCHEMA REFERENCE

### Current Models (SQLAlchemy)

```python
class Database(Base):
    id: int (PK)
    name: str
    description: str (nullable)
    created_at: datetime
    updated_at: datetime
    # Relations: properties, records

class Property(Base):
    id: int (PK)
    db_id: int (FK → Database)
    name: str
    type: str  # text, number, date, checkbox, select, url
    options: JSON (nullable)
    # NEW: ai_type, ai_prompt, auto_update, source_properties

class Record(Base):
    id: int (PK)
    db_id: int (FK → Database)
    data: JSON
    created_at: datetime
    updated_at: datetime

class Embedding(Base):
    id: int (PK)
    record_id: int (FK → Record)
    text: str

class Page(Base):
    id: int (PK)
    title: str
    icon: str (nullable)
    content: JSON  # Block-based content
    parent_id: int (FK → Page, nullable)
    created_at: datetime
    updated_at: datetime
```

### New Models to Add

```python
class AIProperty(Base):        # AI-powered database properties
class Agent(Base):             # Autonomous agent definitions
class AgentRun(Base):          # Agent execution history
class Connector(Base):         # External connector configs
class ConnectorIndex(Base):    # Indexed external content
class MeetingNote(Base):       # Meeting transcriptions
class MeetingActionItem(Base)  # Extracted action items
class AIUsageLog(Base)         # AI usage analytics
class UserPreference(Base)     # User AI preferences
```

---

## 14. KEY FILE PATHS

```
# Configuration
CLAUDE.md                                          → This file
docker-compose.yml                                 → Docker stack
.env                                               → Environment variables
agent/.env                                         → AI service env
agent/alembic.ini                                  → Migration config

# Backend API
agent/orchestrator/main.py                         → Main API (port 8000)
agent/orchestrator/llm.py                          → LLM service
agent/orchestrator/logic.py                        → Business logic
agent/orchestrator/embeddings.py                   → Embedding service

# AI Plugin Service
agent/ai_plugin/api/app.py                         → Plugin API (port 8001)
agent/ai_plugin/capabilities/writing.py            → Writing AI
agent/ai_plugin/capabilities/database_ai.py        → Database AI
agent/ai_plugin/capabilities/workspace_qa.py       → Q&A Engine
agent/ai_plugin/providers/base.py                  → Provider interface
agent/ai_plugin/core/engine.py                     → AI Engine

# Database
agent/db/database.py                               → SQLAlchemy engine
agent/db/models.py                                 → ORM models
agent/db/service.py                                → CRUD operations
agent/db/vector_store.py                           → Qdrant integration

# Frontend
appflowy/frontend/appflowy_flutter/lib/ai/         → Flutter AI layer
appflowy/frontend/appflowy_flutter/lib/main.dart   → Flutter entry

# Tests
agent/tests/litmus_unit_test.py                    → Unit tests
agent/tests/litmus_api_test.py                     → API tests
agent/tests/litmus_e2e_test.py                     → E2E tests
```

---

## 15. ENVIRONMENT VARIABLES

```bash
# Database
POSTGRES_USER=appflowy
POSTGRES_PASSWORD=<secure_password>
POSTGRES_DB=appflowy_ai
DATABASE_URL=postgresql://appflowy:<password>@postgres:5432/appflowy_ai

# Vector Database
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=agent_records

# Redis
REDIS_URL=redis://redis:6379

# LLM - Local
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=gpt-oss:20b
EMBEDDING_MODEL=nomic-embed-text

# LLM - Cloud (Optional)
OPENAI_API_KEY=<your_key>
ANTHROPIC_API_KEY=<your_key>
GOOGLE_API_KEY=<your_key>

# AI Service
AI_DEFAULT_PROVIDER=ollama
AI_MAX_TOKENS=2000
AI_TEMPERATURE=0.7

# Frontend
API_BASE_URL=http://localhost:8000
AI_SERVICE_URL=http://localhost:8001

# Object Storage
MINIO_ROOT_USER=minio
MINIO_ROOT_PASSWORD=<secure_password>
MINIO_ENDPOINT=http://minio:9000

# Connectors (Phase 5)
SLACK_BOT_TOKEN=<token>
SLACK_SIGNING_SECRET=<secret>
GOOGLE_CLIENT_ID=<id>
GOOGLE_CLIENT_SECRET=<secret>
GITHUB_TOKEN=<token>
JIRA_API_TOKEN=<token>
JIRA_BASE_URL=<url>
```

---

## 16. TROUBLESHOOTING & COMMON ISSUES

### Docker Issues

| Issue | Solution |
|-------|---------|
| Container won't start | Check `docker compose logs <service>` for errors |
| Port already in use | `lsof -i :<port>` to find and kill conflicting process |
| Build fails on dependencies | Clear cache: `docker compose build --no-cache <service>` |
| Ollama no GPU | Ensure NVIDIA Docker runtime installed |
| Database connection refused | Verify postgres health check passes before backend starts |
| Old code after restart | Always `docker compose build` before `docker compose up -d` |

### AI/LLM Issues

| Issue | Solution |
|-------|---------|
| Ollama slow responses | Ensure model is pulled: `docker exec ollama ollama pull gpt-oss:20b` |
| Embedding dimension mismatch | Verify nomic-embed-text produces 768-dim vectors |
| Q&A returns no results | Check Qdrant collection has indexed documents |
| Provider timeout | Increase timeout in provider config or switch to smaller model |

### Testing Issues

| Issue | Solution |
|-------|---------|
| Tests fail in Docker | Ensure test DB is separate from production DB |
| Flaky vector search tests | Use deterministic embeddings or mock in unit tests |
| Migration errors | Run `alembic downgrade -1` then `alembic upgrade head` |

---

## QUICK REFERENCE CARD

```
┌────────────────────────────────────────────────┐
│              DEVELOPMENT CHECKLIST              │
│                                                 │
│  For EVERY task:                                │
│  □ Read CLAUDE.md (this file)                   │
│  □ Check which phase the feature belongs to     │
│  □ Write code following modular architecture    │
│  □ Write unit + integration + litmus tests      │
│  □ Ensure 90%+ test coverage                    │
│  □ Update docker-compose.yml if needed          │
│  □ docker compose build <service>               │
│  □ docker compose up -d                         │
│  □ docker compose exec <svc> pytest tests/ -v   │
│  □ Run litmus_test.sh                           │
│  □ git add . && git commit && git push          │
│  □ Update this CLAUDE.md if architecture changes│
└────────────────────────────────────────────────┘
```

---

*Last Updated: 2026-02-12*
*Project: AppFlowy AI (Notion AI Clone)*
*Phase: Starting Phase 1 — Docker Infrastructure*
