# ZENITH — Curriculum-Aware Adaptive Learning Platform

[![ZENITH](https://img.shields.io/badge/Product-ZENITH-000000?style=for-the-badge&logo=target)](https://github.com/Leeladhar-Kaluru/SETU-Adaptive-Learning-Platform)
[![Tests](https://img.shields.io/badge/E2E_Tests-191%2F191_Passed_(100%25)-success?style=for-the-badge&logo=pytest)](TEST_READY.md)
[![Math Verification](https://img.shields.io/badge/SymPy_Math-128%2F128_Verified-blue?style=for-the-badge&logo=python)](e2e_tests/tier1_features/test_f06_sympy_math.py)
[![Mobile Audit](https://img.shields.io/badge/Mobile_Viewport-0px_Overflow_(390px)-brightgreen?style=for-the-badge&logo=googlechrome)](#mobile-responsiveness)
[![Frontend](https://img.shields.io/badge/Frontend-React_19_+_TypeScript_+_Vite-61DAFB?style=for-the-badge&logo=react)](https://react.dev)
[![Backend](https://img.shields.io/badge/Backend-FastAPI_+_Python_3.12-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Database](https://img.shields.io/badge/Database-Supabase_PostgreSQL_17_+_pgvector-336791?style=for-the-badge&logo=postgresql)](https://supabase.com)
[![AI Provider](https://img.shields.io/badge/AI_Inference-Groq_API_(GPT--OSS--120B)-F55036?style=for-the-badge&logo=openai)](https://groq.com)

> **ZENITH** is an offline-first, curriculum-aware adaptive learning desk engineered for Indian school education (Classes 6–10). Built on a neo-brutalist "Kite & Chalk" design system, ZENITH combines **4-parameter Bayesian Knowledge Tracing (BKT)**, **directed acyclic graph (DAG) prerequisite gap analysis**, **SymPy-verified mathematical question banks**, and **a grounded Socratic AI tutor (Groq API)** with bracketed citations, delivering guaranteed pedagogy without LLM hallucinations.

---

## 🌟 Executive Summary & Technical Innovations

1. **100% Deterministic Concept Mastery (Zero Hallucination)**:
   Diagnostic scoring, mastery progression, and prerequisite gap traversal operate completely independently of LLM availability. Mastery is computed via 4-parameter Bayesian Knowledge Tracing ($p(L_0)=0.25, p(T)=0.15, p(G)=0.20, p(S)=0.10$) with backward Breadth-First Search (BFS) over Kahn-validated curriculum DAGs.
2. **SymPy-Verified Mathematical Question Engine**:
   Every question item (128 items across 4 CBSE Class 10 Mathematics chapters) is verified by Python's SymPy computer algebra solver. Quadratic roots, discriminant signs ($b^2 - 4ac$), and linear systems are mathematically validated before being served to students.
3. **Grounded Socratic AI Tutor with Strict Citations**:
   Powered by the high-throughput Groq API (`openai/gpt-oss-120b` primary with `qwen/qwen3.8-27b` fallback). Adheres to strict Socratic pedagogical rules (never gives away answers; prompts stepwise reasoning) and extracts numbered citations (`[1]`, `[2]`) pointing to exact curriculum textbooks. Capped at 1,500 tokens with automatic exponential backoff on HTTP 429 and graceful 503 degradation.
4. **"Kite & Chalk" Neo-Brutalist Design System**:
   Crafted with `#FDFBF7` canvas, `#18181B` high-contrast ink borders, pastel semantic tiles, and brutalist drop-shadows. Fully responsive across 390px mobile viewports with 0px horizontal overflow, tactile KaTeX formula rendering, and full keyboard/screen-reader accessibility.
5. **Offline-First PWA with Dexie v3**:
   Supports zero-connectivity study. Lesson packages, practice quizzes, and student attempt queues persist locally in IndexedDB (Dexie v3) and synchronize idempotently when internet connectivity resumes.
6. **Production Dual-Cloud Deployment**:
   Containerized Python 3.12-slim backend running on Render with non-root security (`USER appuser`) and automated Alembic schema migrations on boot. Frontend statically optimized and hosted on Vercel with SPA rewrites and modern security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`).

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Client ["Frontend: The Learning Desk (React 19 + TypeScript + Vite + PWA)"]
        UI["'Kite & Chalk' Neo-Brutalist UI\n(CSS Modules + Custom Design Tokens)"]
        KaTeX["KaTeX Formula Engine\n(Genuine LaTeX Math Rendering)"]
        DexieDB["Local-First Offline Storage\n(IndexedDB via Dexie.js v3)"]
        Reader["Interactive Lesson Reader\n(Concepts, Formulas, Worked Steps)"]
        QuizUI["Adaptive Practice Arena\n(SymPy-Verified Items + Hints)"]
        TutorUI["Ask ZENITH Socratic Drawer\n(Numbered Citations [1], [2])"]
        DAGView["Interactive Concept DAG Map\n(SVG Prerequisite Topology)"]
    end

    subgraph CloudVercel ["Frontend Hosting (Vercel Edge CDN)"]
        SPA["Vercel SPA Rewrites\n(/index.html + Immutable Assets)"]
        VercelSec["Security Headers\n(nosniff, DENY, strict-origin)"]
    end

    subgraph Backend ["Backend API Service (Render Docker Container - Python 3.12)"]
        FastAPI["FastAPI 0.115 Core\n(Lifespan Workers + Async Event Loop)"]
        Security["Auth & Security Gates\n(Bearer JWT + Security Headers)"]
        BKTEngine["4-Parameter BKT Math Engine\n(p(L0)=0.25, p(T)=0.15, p(G)=0.20, p(S)=0.10)"]
        DAGEngine["Prerequisite Gap Traversal\n(Kahn's DAG + Backward BFS)"]
        Gamification["Gamification Service\n(Asia/Kolkata Streaks + Zenith Coins + Badges)"]
        Redactor["Question Payload Redactor\n(Zero-Leak answerKey Stripping)"]
    end

    subgraph AICloud ["Multi-Provider AI Tier"]
        Groq["Groq Cloud API\n(openai/gpt-oss-120b @ 500 T/s)"]
        FallbackModel["Fallback Groq Model\n(qwen/qwen3.8-27b)"]
        LMStudio["LM Studio Local Gateway\n(127.0.0.1:1234 / Gemma 4 E4B)"]
    end

    subgraph DataCloud ["Cloud Persistence (Supabase PostgreSQL 17 + Storage)"]
        PG["PostgreSQL 17 Database\n(17 RLS-Protected Tables)"]
        PGVector["pgvector Extension\n(768d Cosine Distance <=>)"]
        S3["Supabase Object Storage\n('setu-documents' Bucket)"]
    end

    Client --> SPA
    SPA --> FastAPI
    FastAPI --> PG
    FastAPI --> PGVector
    FastAPI --> S3
    FastAPI --> Groq
    Groq -.-> FallbackModel
    FastAPI -.-> LMStudio
    UI <--> DexieDB
```

---

## 📊 Comprehensive Test Metrics Ledger

Empirical verification executed against real database instances and API contracts:

| Metric Category | Specification | Verified Status | Evidence Location |
|---|---|---|---|
| **E2E Test Suite** | 4 Tiers, 28 Features, Boundaries, Scenarios | **191 / 191 Passed (100%)** | `e2e_tests/` (19.42s execution) |
| **SymPy Mathematics** | Roots, discriminant, arithmetic identities | **128 / 128 Items (100%)** | `e2e_tests/tier1_features/test_f06_sympy_math.py` |
| **Curriculum Content** | CBSE Class 10 Math (Ch 1–4) | **4 Chapters, 20 Packages** | `backend/app/content/library/cbse-10-math/` |
| **Diagnostic Banks** | 6 core + 2 prerequisite diagnostic probes | **4 Banks (32 Probes)** | `e2e_tests/tier1_features/test_f12_diagnostics_practice.py` |
| **BKT Math Engine** | Canonical parameters $L_0, T, G, S$ | **Floor 0.0001, Ceiling 0.9999** | `e2e_tests/tier1_features/test_f10_bkt_engine.py` |
| **Timezone Streaks** | Midnight rollover in `Asia/Kolkata` | **Zero Drift / Idempotent** | `e2e_tests/tier2_boundaries/test_b05_asia_kolkata_midnight_streaks.py` |
| **Mobile Responsiveness** | Viewport width 390px (iPhone 14/Pixel 7) | **0px Horizontal Overflow** | `scratch/diagnose_overflow.cjs` (5/5 routes) |
| **Question Security** | Student payload answerKey redaction | **0 Leaks Across All APIs** | `e2e_tests/tier1_features/test_f08_question_redaction.py` |
| **Database Security** | Row Level Security (RLS) enforcement | **17 Tables Protected** | `e2e_tests/tier1_features/test_f02_models_schema.py` |
| **AI Degradation** | Groq offline or HTTP 429 rate limit | **Honest 503 Fallback** | `e2e_tests/tier2_boundaries/test_b01_ai_rate_limits_and_429.py` |

---

## ⏱️ Structured 3-Minute Judge Demonstration Script

### Minute 1 (0:00 – 1:00) — Problem, Curriculum Engine & Neo-Brutalist Desk
- **[0:00 - 0:20] Hook & Problem**:
  - *Action*: Present the landing screen and navigate to the student dashboard (`/`).
  - *Narration*: *"Welcome to ZENITH. Traditional EdTech suffers from two fatal flaws: ungrounded AI chatbots that hallucinate mathematical formulas, and rigid platforms that cannot diagnose why a student is struggling. ZENITH solves this by combining 100% deterministic Bayesian knowledge tracing with SymPy-verified curriculum mathematics and grounded Socratic AI tutoring."*
- **[0:20 - 0:40] "Kite & Chalk" Neo-Brutalist Desk**:
  - *Action*: Showcase the high-contrast dashboard with live streak calendar (Asia/Kolkata timezone), XP counter, and KaTeX-rendered formula widgets.
  - *Narration*: *"Notice our 'Kite & Chalk' design system: high-contrast borders, tactile pastel tiles, genuine KaTeX math rendering, and strict zero-overflow mobile responsiveness. Every number on this desk is backed by real database records—zero fabricated data."*
- **[0:40 - 1:00] CBSE Class 10 Curriculum & Concept DAG**:
  - *Action*: Open `/explore` and click into "Real Numbers" (`/map/real-numbers`).
  - *Narration*: *"Here is our Kahn's DAG concept map for CBSE Class 10 Real Numbers. Rather than a flat list, concepts like Euclid's Division Lemma and the Fundamental Theorem of Arithmetic exist as a directed prerequisite topology."*

### Minute 2 (1:00 – 2:00) — 4-Parameter BKT & Directed DAG Prerequisite Remediation
- **[1:00 - 1:25] Diagnostic Assessment Sitting**:
  - *Action*: Launch the Diagnostic Sit-In (`/practice?mode=diagnostic`).
  - *Narration*: *"Watch our 8-probe diagnostic state machine in action. The student is presented with calibrated questions where answer keys are strictly redacted on the server. We deliberately select incorrect answers on foundational divisibility."*
- **[1:25 - 1:45] Backward BFS Gap Traversal**:
  - *Action*: Submit diagnostic. The screen reveals a detected prerequisite gap.
  - *Narration*: *"Look at what happened: ZENITH's backward BFS traversal identified two consecutive errors on prerequisite concepts. Our 4-parameter BKT engine immediately calculated posterior mastery probability drop and flagged 'Prerequisite Gap Detected'."*
- **[1:45 - 2:00] Dynamic Remediation & Smart Practice**:
  - *Action*: Click "Start Targeted Practice" to view the recommended remedial lesson.
  - *Narration*: *"Instead of penalizing the student, ZENITH injects a targeted remedial learning loop and unlocks gamification XP and streak milestones upon mastery recovery."*

### Minute 3 (2:00 – 3:00) — Grounded Socratic AI Tutor, Cloud Architecture & Production Smoke
- **[2:00 - 2:30] Grounded Socratic AI Tutor with Numbered Citations**:
  - *Action*: Open Ask ZENITH drawer (`/ask`), type: *"Can you give me the answer to question 3 on irrational numbers?"*
  - *Narration*: *"Here is our Socratic AI tutor running on Groq's high-speed inference engine. Notice rule #1: it refuses to give the direct answer. Instead, it guides the student step-by-step and cites exact curriculum textbook paragraphs with clickable bracketed citations [1]. If Groq encounters rate limits or network issues, ZENITH gracefully drops to an honest 503 availability message without ever disrupting the student's mastery."*
- **[2:30 - 2:45] Production Architecture (Vercel + Render)**:
  - *Action*: Display `render.yaml`, `backend/Dockerfile`, and `frontend/vercel.json`.
  - *Narration*: *"Under the hood, ZENITH runs on a production-hardened dual-cloud stack: a statically compiled React 19 SPA on Vercel with immutable asset caching and strict security headers, and an asynchronous FastAPI Docker container on Render with Supabase PostgreSQL 17 and pgvector."*
- **[2:45 - 3:00] Automated Production Smoke Verification**:
  - *Action*: Run `powershell ./scripts/smoke_production.ps1`.
  - *Narration*: *"Finally, our automated production smoke script verifies all 6 core pillars in real time: health, catalogue, chapter packages, CORS negotiation, security headers, and live Socratic inference. All 191 E2E tests pass with 100% reliability. That is ZENITH—curriculum-aware, mathematically verified, and production ready."*

---

## 🚀 Running Locally & Verification

### 1. Complete E2E Test Suite
```powershell
cd "c:\projects\setu - V2"
.\backend\.venv\Scripts\python.exe -m pytest e2e_tests/ -v
```

### 2. Automated Production Smoke Verification
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_production.ps1 -TargetUrl "http://127.0.0.1:8000"
```

### 3. Local Development Startup
```powershell
# Terminal 1: Backend API
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Frontend Desk
cd frontend
npm run dev
# Accessible at http://localhost:5173
```
