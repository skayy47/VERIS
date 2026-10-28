# VERIS — Production Research Agent

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Anthropic](https://img.shields.io/badge/LLM-Anthropic%20Claude-blueviolet)](https://www.anthropic.com/)
[![Status](https://img.shields.io/badge/status-in%20progress-orange)](./.github/workflows/eval-gate.yml)

Multi-step AI research agent with grounded citations, a 100-query multilingual eval benchmark, and full production observability. No LangChain. No LangGraph. Pure asyncio state machine.

---

## State Machine

```
User query
    ↓
POST /api/research  ──────────────── FastAPI
    ↓
AsyncAgent.run()
    ├─ PLAN    →  decompose into sub-queries          (Haiku 4.5)
    ├─ SEARCH  →  Tavily × N hops                     (TavilySearchTool)
    ├─ REASON  →  synthesise over retrieved context   (Sonnet 4.6)
    ├─ VERIFY  →  cross-check citations               (Sonnet 4.6)
    └─ ANSWER  →  compose + score faithfulness
    ↓
SSE stream  ─────────────────────────── AgentStateUpdate × 5 events
    ↓
Next.js UI  ─────────────────────────── fetch() ReadableStream (not EventSource)
    ↓
MLflow run · OTel span · Evidently drift check
```

Each state transition is a plain Python `await`. Every hop is observable.

---

## Why no framework

LangChain/LangGraph abstract state as a graph. That makes it easy to get started and hard to debug, instrument, or extend without fighting the framework. VERIS owns every transition: you can read the entire orchestrator in one file, add a new state in 15 lines, and wire any tool without checking compatibility matrices.

---

## Stack

| Layer | Choice | Why |
|---|---|---|
| Orchestrator | Custom asyncio state machine | Readable, zero framework lock-in |
| LLM | Anthropic Sonnet 4.6 + Haiku 4.5 | Reasoning vs retrieval cost split |
| Search | Tavily | Clean API, citation-friendly results |
| Backend | FastAPI 0.115 + uvicorn | Async-native, SSE first-class |
| DB | asyncpg + pgvector | Raw SQL, no ORM, vector search |
| Eval | RAGAS-style metrics + VERIS-Bench-100 | Reproducible, CI-gated |
| Tracking | MLflow 2.18 | Per-run cost/latency/faithfulness |
| Tracing | OpenTelemetry → Grafana Tempo | Per-state span granularity |
| Metrics | Prometheus + Grafana | Real-time ops dashboard |
| Drift | Evidently DataDriftPreset | Score distribution alerts |
| Frontend | Next.js 14 + Tailwind + Zustand | SSE streaming, Luminal Void theme |
| Infra | Docker Compose | Postgres, Prometheus, Grafana, MLflow |

---

## Quick Start

### Prerequisites

- Python 3.11+, Node.js 20+, Docker + Compose v2

### 1 — Infra services

```bash
docker compose -f infra/docker-compose.yml up -d postgres prometheus grafana mlflow
```

Grafana → `http://localhost:3030`  
MLflow  → `http://localhost:5050`

### 2 — Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\pip install -e ".[dev]"
cp .env.example .env          # fill in ANTHROPIC_API_KEY + TAVILY_API_KEY
.venv\Scripts\uvicorn api.main:app --port 8001 --reload

# macOS / Linux
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn api.main:app --port 8001 --reload
```

### 3 — Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev                    # http://localhost:3001
```

---

## Eval & Observability

### Run the benchmark

```bash
cd backend
python -m eval.run_eval --sample 10          # quick smoke test
python -m eval.run_eval --sample 100         # full bench (~$3)
python -m eval.run_eval --language ar        # single-language pass
```

Output: faithfulness, citation accuracy, latency, cost — per query and aggregate.  
Results are logged to MLflow automatically when `MLFLOW_TRACKING_URI` is set.

### CI eval gate

`.github/workflows/eval-gate.yml` is designed to run on every PR, where a faithfulness regression >5% blocks the merge (not yet proven in CI — see Phase 3 in the roadmap). This prevents silent quality degradation from prompt or model changes.

### Drift detection

```bash
python -m eval.drift --current eval/results/latest.json --baseline eval/baseline/v1_baseline.jsonl
```

Exits 1 (alert) if score distribution drift > 0.15, 0 otherwise. Wired into `dvc.yaml`.

### Grafana dashboard

Pre-provisioned at `http://localhost:3030` (auto-loaded from `infra/grafana/`):

- Runs / 24h, median faithfulness, p95 latency, mean cost per query
- Per-state latency breakdown (PLAN / SEARCH / REASON / VERIFY / ANSWER)
- Error rate by state, per-language faithfulness, drift score timeline

### Prometheus metrics

| Metric | Type | Description |
|---|---|---|
| `veris_agent_runs_total` | Counter | Total runs by language |
| `veris_agent_state_latency_seconds` | Histogram | Latency per state |
| `veris_agent_total_latency_seconds` | Histogram | End-to-end latency |
| `veris_agent_cost_usd` | Histogram | Cost per run |
| `veris_agent_errors_total` | Counter | Errors by state |
| `veris_eval_faithfulness` | Gauge | Last eval faithfulness |
| `veris_eval_citation_accuracy` | Gauge | Last eval citation accuracy |
| `veris_drift_score` | Gauge | Latest Evidently drift score |

---

## VERIS-Bench-100

100 research queries across 10 languages (EN, FR, AR, ES, DE, JA, ZH, PT, RU, HI), 10 per language.

Each query has:
- `question` — research query
- `category` — tech / science / geopolitics / business / health
- `difficulty` — easy / medium / hard
- `expected_source_domains` — expected authoritative sources
- `expected_facts` — key claims the answer should contain
- `ground_truth_citations` — reference URLs

Located at `backend/eval/data/veris_bench_v1.jsonl`. Generated by `backend/eval/generate_bench.py`.

---

## Project Layout

```
VERIS/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app, lifespan, routers
│   │   ├── deps.py              # session store (only global state)
│   │   ├── models.py            # Pydantic v2 — request/response/streaming
│   │   └── routes/
│   │       ├── research.py      # POST /api/research (SSE)
│   │       ├── health.py        # GET /health
│   │       ├── metrics.py       # GET /api/metrics (eval history)
│   │       └── prometheus.py    # GET /metrics (Prometheus scrape)
│   ├── orchestrator/
│   │   ├── agent.py             # AsyncAgent — the state machine
│   │   ├── tools/
│   │   │   └── search.py        # TavilySearchTool
│   │   └── memory/
│   │       └── episodic.py      # Postgres-backed session memory
│   ├── eval/
│   │   ├── bench.py             # load_bench() — JSONL loader
│   │   ├── run_eval.py          # CLI harness + MLflow logging
│   │   ├── metrics.py           # faithfulness, citation_accuracy
│   │   ├── drift.py             # CLI drift check
│   │   ├── generate_bench.py    # generates veris_bench_v1.jsonl
│   │   └── data/
│   │       └── veris_bench_v1.jsonl
│   ├── ops/
│   │   ├── otel.py              # OTel init + state_span() + Prometheus metrics
│   │   ├── mlflow_tracker.py    # MLflowTracker — eval + production logging
│   │   └── drift.py             # DriftMonitor (Evidently)
│   └── utils/
│       └── config.py            # pydantic-settings — Settings singleton
├── frontend/
│   └── src/
│       ├── app/                 # Next.js 14 app router
│       ├── components/          # StreamingView, CitationCard, StateTimeline
│       └── stores/              # Zustand — research session state
├── infra/
│   ├── docker-compose.yml
│   ├── prometheus/
│   │   └── prometheus.yml
│   └── grafana/
│       ├── dashboards/
│       │   └── veris-ops.json   # pre-provisioned ops dashboard
│       └── provisioning/        # auto-loaded by Grafana on startup
├── .github/
│   └── workflows/
│       ├── ci.yml               # lint + type-check + unit tests
│       └── eval-gate.yml        # faithfulness regression gate
└── dvc.yaml                     # bench → eval → drift pipeline
```

---

## Port Map

| Service | Port |
|---|---|
| Backend (uvicorn) | 8001 |
| Frontend (Next.js) | 3001 |
| Postgres | 5433 |
| Prometheus | 9090 |
| Grafana | 3030 |
| MLflow | 5050 |

---

## Invariants

Things that will never change by design:

- No LangChain / LangGraph / LlamaIndex — orchestrator is pure Python
- No ORM — asyncpg + raw SQL only
- No global mutable state — session store in `api/deps.py` is the only exception
- No `print()` in committed code — structured logging via `logging` module
- Heavy deps (`mlflow`, `evidently`, `opentelemetry`) lazy-imported inside function bodies
- Every file starts with `from __future__ import annotations`

---

## Roadmap

- [x] Phase 1 — Ops layer (OTel, Prometheus, MLflow, Evidently, Grafana dashboard)
- [x] Phase 2 — VERIS-Bench-100 (100 queries × 10 languages, DVC pipeline)
- [ ] Phase 3 — CI eval gate proof + architecture diagram
- [ ] Phase 4 — PyPI package + HuggingFace dataset publish
- [ ] Phase 5 — Railway deploy + Vercel deploy + demo recording

---

## License

MIT — see [LICENSE](LICENSE).
