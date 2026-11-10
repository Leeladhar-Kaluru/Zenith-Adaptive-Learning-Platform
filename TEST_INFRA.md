# ZENITH — End-to-End Test Infrastructure & Methodology Specification (TEST_INFRA.md)

## 1. Executive Summary & Core Philosophy

ZENITH requires an uncompromised, evidence-based verification standard. The End-to-End (E2E) testing track is constructed as an **Opaque-Box, Requirement-Driven, Multi-Tier Test Suite** that evaluates the system strictly against its functional contracts, interface definitions, mathematical invariants, and user workflows.

### 1.1 Opaque-Box Principles
1. **Public Surface Only**: Tests interact with ZENITH exclusively through external interfaces: public HTTP REST/FastAPI endpoints, CLI verification scripts, environment configurations, and static asset builds. Internal database sessions or private module state are never monkeypatched in tests.
2. **Authoritative Specification Sources**: Every test assertion is derived directly from:
   - `c:\projects\setu - V2\.agents\teamwork\ORIGINAL_REQUEST.md` (Groq API, timeouts, 429 backoff, model selection, non-AI decoupling, Nomic embeddings isolation, honest availability messaging).
   - `c:\projects\setu - V2\.agents\teamwork\PROJECT.md` (Feature Inventory 1–28, Interface Contracts, Code Layout).
   - `zenith_rebuild_implementation_plan.md` (BKT parameters, concept DAG rules, Asia/Kolkata timezone streaks, 20 CBSE 10 Math packages, Kite & Chalk design tokens, Vercel/Render deployments).
3. **Progressive Testability & Dual-Mode Execution**:
   - **Mode A (Live Server)**: When `E2E_API_BASE_URL` is set (e.g., `http://localhost:8000` or production Render URL), tests execute via real HTTP network calls using `httpx.Client`.
   - **Mode B (In-Process ASGI)**: When run in headless/CI environments where a standalone daemon is not running, the harness utilizes `httpx.ASGITransport(app=app)` to exercise the exact same FastAPI application stack without requiring an open network port.
4. **Independent & Isolated**: Each test case provisions its own unique user context (via `X-User-Id` / Bearer token simulation), avoids execution-order coupling, and handles cleanup or non-interfering isolation.

---

## 2. The 4-Tier Test Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │    Tier 4: Real-World Student Journeys       │
                    │    - CBSE Class 10 Math End-to-End Journey   │
                    │    - Onboard -> Diagnose -> Learn -> Tutor   │
                    │      -> Practice -> Streak & Badge Unlock    │
                    └───────────────────────┬──────────────────────┘
                                            │
                    ┌───────────────────────▼──────────────────────┐
                    │   Tier 3: Cross-Feature Pairwise Invariants  │
                    │   - Diagnostic -> BKT -> Recs -> Rewards     │
                    │   - Seed -> Redaction -> Catalog Retrieval   │
                    │   - Socratic Doubt -> Quota -> 503 Fallback  │
                    │   - Offline Sync -> Idempotent Reconnection  │
                    └───────────────────────┬──────────────────────┘
                                            │
                    ┌───────────────────────▼──────────────────────┐
                    │   Tier 2: Boundary, Stress & Corner Cases    │
                    │   - HTTP 429 Exponential Backoff & Headers   │
                    │   - Midnight Asia/Kolkata Streak Transitions │
                    │   - Empty/Max Payloads & 1500 Token Caps     │
                    │   - Extreme BKT Bounds (0.0001 to 0.9999)    │
                    │   - Redaction Leaks & Idempotency Collisions │
                    └───────────────────────┬──────────────────────┘
                                            │
                    ┌───────────────────────▼──────────────────────┐
                    │     Tier 1: Feature Coverage (28 Features)   │
                    │     >= 5 Distinct Test Cases per Feature     │
                    │     Total: 140+ Authoritative Feature Tests   │
                    └──────────────────────────────────────────────┘
```

### Tier Breakdown
- **Tier 1 (Feature Coverage)**: Comprehensive validation across all 28 features in `PROJECT.md § Feature Inventory`. Requires $\ge 5$ test cases per feature (140+ feature tests).
- **Tier 2 (Boundary & Corner Cases)**: Edge conditions, invalid inputs, boundary values, resource caps, and failure simulations ($\ge 5$ cases per area, 40+ tests).
- **Tier 3 (Cross-Feature Pairwise)**: Inter-service contracts and multi-step transaction pipelines verifying that system subsystems interact cleanly without contract drift (20+ tests).
- **Tier 4 (Real-World Scenarios)**: High-fidelity student persona simulation executing the complete flagship CBSE Class 10 Mathematics learning loop (10+ tests).

---

## 3. Directory Layout & Harness Structure

All tests reside under `e2e_tests/` in the project root:

```
c:\projects\setu - V2\
├── e2e_tests/
│   ├── conftest.py                             # Pytest fixtures, ASGI transport, auth, environment
│   ├── test_config.py                          # Global E2E test configuration & endpoints
│   ├── helpers/
│   │   ├── __init__.py
│   │   ├── api_client.py                       # Unified opaque-box client wrapping httpx
│   │   ├── auth.py                             # Student/Teacher/Anonymous session generators
│   │   ├── bkt_oracle.py                       # Authoritative BKT mathematical reference oracle
│   │   └── math_verifier.py                    # Sympy mathematical truth oracle
│   ├── tier1_features/                         # 28 Feature coverage modules (>= 5 tests each)
│   │   ├── __init__.py
│   │   ├── test_f01_inventory_safety.py        # Feature 1: DB Inventory & safety checks
│   │   ├── test_f02_models_schema.py           # Feature 2: Migration 009 & DB models
│   │   ├── test_f03_groq_ai_adapter.py         # Feature 3: Multi-Provider AI Adapter & Groq
│   │   ├── test_f04_decoupled_embeddings.py    # Feature 4: Decoupled Embeddings & BM25
│   │   ├── test_f05_validator_seed.py          # Feature 5: Curriculum Validator & Seed CLI
│   │   ├── test_f06_sympy_math.py              # Feature 6: Sympy Mathematical Verification
│   │   ├── test_f07_cbse10_content.py          # Feature 7: CBSE 10 Math Content Packages
│   │   ├── test_f08_question_redaction.py      # Feature 8: Question Package Redaction
│   │   ├── test_f09_library_catalog_api.py     # Feature 9: Library Catalog & Access APIs
│   │   ├── test_f10_bkt_engine.py              # Feature 10: BKT Engine & Gap Detection
│   │   ├── test_f11_gamification_rewards.py    # Feature 11: Rewards, Streaks & Badges
│   │   ├── test_f12_diagnostics_practice.py    # Feature 12: Diagnostic Session & Practice
│   │   ├── test_f13_socratic_tutor.py          # Feature 13: Socratic AI Tutor & Citations
│   │   ├── test_f14_design_tokens.py           # Feature 14: "Kite & Chalk" CSS Tokens
│   │   ├── test_f15_ui_primitives.py           # Feature 15: UI Primitives & Navigation
│   │   ├── test_f16_dashboard_analytics.py     # Feature 16: Student Dashboard & Analytics
│   │   ├── test_f17_explore_chapter_pages.py   # Feature 17: Curriculum Explore & Chapter
│   │   ├── test_f18_lesson_reader.py           # Feature 18: Lesson Reader & LaTeX
│   │   ├── test_f19_practice_arena.py          # Feature 19: Practice Arena & Runner
│   │   ├── test_f20_concept_dag_map.py         # Feature 20: Accessible Concept DAG Map
│   │   ├── test_f21_achievements_pages.py      # Feature 21: Achievements & My Learning
│   │   ├── test_f22_offline_sources.py         # Feature 22: Offline Dexie v3 & Sources
│   │   ├── test_f23_vercel_deployment.py       # Feature 23: Vercel Deployment Config
│   │   ├── test_f24_docker_render.py           # Feature 24: Backend Docker & Render Config
│   │   ├── test_f25_smoke_script.py            # Feature 25: Production Smoke Script
│   │   ├── test_f26_test_suite_contracts.py    # Feature 26: Comprehensive E2E Test Suite
│   │   ├── test_f27_live_groq_verification.py  # Feature 27: Live Groq End-to-End AI
│   │   └── test_f28_adversarial_hardening.py   # Feature 28: Adversarial Hardening
│   ├── tier2_boundaries/                       # Boundary, corner, rate limit & stress
│   │   ├── __init__.py
│   │   ├── test_b01_ai_rate_limits_and_429.py
│   │   ├── test_b02_empty_and_oversized_payloads.py
│   │   ├── test_b03_token_caps_and_timeouts.py
│   │   ├── test_b04_zero_score_and_extreme_mastery.py
│   │   ├── test_b05_asia_kolkata_midnight_streaks.py
│   │   ├── test_b06_invalid_options_and_mcq_bounds.py
│   │   └── test_b07_idempotency_collisions.py
│   ├── tier3_cross_feature/                    # Cross-feature pipelines
│   │   ├── __init__.py
│   │   ├── test_cf01_diagnostic_bkt_practice_rewards.py
│   │   ├── test_cf02_seed_catalog_redaction_flow.py
│   │   ├── test_cf03_tutor_citations_quota_degradation.py
│   │   └── test_cf04_offline_cache_sync_flow.py
│   └── tier4_real_world/                       # Complete student journey
│       ├── __init__.py
│       └── test_rw01_cbse10_math_student_journey.py
├── TEST_INFRA.md                               # This specification document
└── TEST_READY.md                               # Orchestrator delivery report & matrix
```

---

## 4. Authoritative Expected Output Derivation Matrix

| Feature | Input Specification | Expected Observable Output | Authoritative Source |
|---|---|---|---|
| **F01: Inventory & Safety** | `python -m scripts.inventory_db` | Zero duplicate constraint violations, valid table counts recorded | Plan Track 1, `PROJECT.md` |
| **F02: Schema & Models** | Inspection of Alembic 009 & SQLAlchemy Base | All 17 new models exported (`concepts`, `bkt_states`, `tutor_threads`, etc.) | Plan Track 1, Migration 009 |
| **F03: Multi-Provider AI** | `LLM_PROVIDER="groq"`, prompt text | Groq endpoint `https://api.groq.com/openai/v1`, models `openai/gpt-oss-120b`, fallback `qwen/qwen3.8-27b`, 429 exponential backoff, max 1500 tokens | Req 1-9, `PROJECT.md § AI Inference` |
| **F04: Decoupled Embeddings** | Search queries & embedding endpoint | Nomic 768d embeddings isolated from chat; library retrieval uses fast keyword/BM25 | Req 12, Plan Track 1/2 |
| **F05: Validator & Seed CLI** | Content manifest & JSON packages | Kahn's algorithm verifies DAG acyclicity; required fields present; `sourceRefs` strictly enforced | Plan Track 2, `PROJECT.md` |
| **F06: Sympy Math** | Question equation strings and answer keys | Sympy solver verifies roots, expressions, and identities with 0 arithmetic errors | Plan Track 2, `PROJECT.md` |
| **F07: CBSE 10 Math Content** | 4 chapters (Real Numbers, Polynomials, Linear, Quadratic) | 20 resources (lesson, worked-ex, revision, formula, practice) + 4 diagnostic banks | Plan Track 2, `PROJECT.md` |
| **F08: Question Redaction** | `GET /api/v1/library/resources/{id}` for student | Payload contains question text and options; `answerKey` and private explanations are stripped | Plan Track 2, `PROJECT.md` |
| **F09: Library Catalog APIs** | `GET /api/v1/library/catalogue` | Returns list of chapters and subjects; published content accessible; drafts hidden | `PROJECT.md § Interface Contracts` |
| **F10: BKT Engine** | Student response correctness sequence | $p(L_{t}) = p(L_{t\vert obs}) + (1 - p(L_{t\vert obs})) \cdot p(T)$, $p(L_0)=0.25, p(T)=0.15, p(G)=0.20, p(S)=0.10$. Gap detected when errors $\ge 2$ | Plan Track 3, `PROJECT.md` |
| **F11: Gamification & Rewards** | Submit quiz attempt ID | Idempotent award issuance (`attempt:{id}`); streaks evaluated in `Asia/Kolkata`; badges awarded | Plan Track 3, `PROJECT.md` |
| **F12: Diagnostics & Practice** | Start diagnostic session | 6 core items + dynamic prerequisite probes on error; weakest gap targeted | Plan Track 3, `PROJECT.md` |
| **F13: Socratic AI Tutor** | Post student question with context | Response contains numbered citations `[1]`; daily message quota tracked; 503 fallback if Groq offline | Req 10, Plan Track 3 |
| **F14: Design System Tokens** | `frontend/src/tokens.css` inspection | Canvas `#FDFBF7`, Ink `#18181B`, pastels (amber, blue, coral, peach, mint), 1.5px borders, neo-brutalist shadows | Plan Track 4, `PROJECT.md` |
| **F15: UI Primitives** | Component exports in `frontend/src/components/ui` | Reusable Button, Card, Badge, ProgressRing, left navigation rail matching Kite & Chalk | Plan Track 4 |
| **F16: Dashboard & Analytics** | `GET /api/v1/rewards/me`, dashboard route | Gamification stats (XP, level, streak, badges), course progress %, daily challenge mascot | Plan Track 4 |
| **F17: Explore & Chapter** | Navigation to `/explore` and `/chapter/:slug` | Board/class/subject filtering, 5 resource package cards, diagnostic CTA | Plan Track 4 |
| **F18: Lesson Reader** | `/learn/:lessonId` | Section-by-section reader, LaTeX equations, worked examples, Ask Zenith trigger | Plan Track 4 |
| **F19: Practice Arena** | `/practice` route & question runner | Interactive question flow, immediate feedback, scratchpad, XP toast | Plan Track 4 |
| **F20: Accessible DAG Map** | `/map` route | SVG DAG nodes with mastery states, keyboard navigable, detail drawer | Plan Track 4 |
| **F21: Achievements & Learning** | `/achievements` & `/my-learning` | Badge showcase, monthly streak calendar, in-progress & offline tabs | Plan Track 4 |
| **F22: Offline Dexie & Sources** | Dexie schema & `/sources` route | Offline package storage in IndexedDB, textbook upload flow preserved | Plan Track 4, `PROJECT.md` |
| **F23: Vercel Deployment** | `frontend/vercel.json` & `api.ts` | SPA rewrites to `/index.html`, dynamic `VITE_API_BASE_URL` routing | Req 29, Plan Track 5 |
| **F24: Docker & Render** | `backend/Dockerfile` & `render.yaml` | Python 3.12-slim container, migration on startup, `/api/v1/health` check | Plan Track 5 |
| **F25: Smoke Script** | `scripts/smoke_production.ps1` | Tests health, catalogue, chapter, CORS, security headers, Groq AI call | Plan Track 5 |
| **F26: Comprehensive E2E** | Test runner execution | All 4 Tiers execute with 100% pass rate; authoritative reports produced | Plan Track Final |
| **F27: Live Groq Verification** | End-to-end AI request | Real inference against Groq endpoint using `GROQ_API_KEY` | Req 13, 23 |
| **F28: Adversarial Hardening** | Stress tests & boundary probes | Zero unhandled 500s; prompt injections isolated; malformed inputs rejected | Plan Track Final |

---

## 5. Non-Deterministic Handling & Invariant Testing

1. **UUIDs and Identifiers**:
   - Tests assert string formats matching standard UUIDv4 regex (`^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`).
2. **Timestamps**:
   - Tested for ISO 8601 formatting and monotonic progression.
3. **Asia/Kolkata Streaks**:
   - Streaks are calculated based on calendar day boundaries in the `Asia/Kolkata` timezone (UTC + 5:30). A test simulates attempts at 23:58 IST and 00:02 IST next day to verify streak increment.
4. **LLM Output Variability**:
   - While exact text varies, contract invariants are deterministic:
     - Must return a non-empty string.
     - Must not exceed token ceilings (max 1500 tokens).
     - Must contain valid citation formats `[1]`, `[2]` when referencing retrieved content.
     - Must return HTTP 503 degraded status when provider is offline rather than hanging or returning HTTP 500.

---

## 6. Execution Instructions

To execute the entire E2E test suite:

```powershell
# Using the backend python virtual environment
cd "c:\projects\setu - V2"
.\backend\.venv\Scripts\python.exe -m pytest e2e_tests/ -v

# Run by specific tier:
.\backend\.venv\Scripts\python.exe -m pytest e2e_tests/tier1_features/ -v
.\backend\.venv\Scripts\python.exe -m pytest e2e_tests/tier2_boundaries/ -v
.\backend\.venv\Scripts\python.exe -m pytest e2e_tests/tier3_cross_feature/ -v
.\backend\.venv\Scripts\python.exe -m pytest e2e_tests/tier4_real_world/ -v
```
