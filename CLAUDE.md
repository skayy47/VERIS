# VERIS — Project Intelligence

## What this is

Production research agent. Custom asyncio state machine (no LangChain/LangGraph/LlamaIndex).
State machine: PLAN → SEARCH → REASON → VERIFY → ANSWER.
Evaluated on VERIS-Bench-100. Ops: MLflow + OTel + Evidently + Prometheus/Grafana.

## Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI 0.115+ / uvicorn / pydantic v2 |
| DB | asyncpg + pgvector (reuses nexus Supabase instance) |
| LLM | anthropic SDK — Sonnet 4.6 (reasoning) + Haiku 4.5 (retrieval) |
| Search | tavily-python |
| Eval | RAGAS-style metrics, VERIS-Bench-100, CI gate |
| Tracking | MLflow 2.18 |
| Tracing | OpenTelemetry (OTLP → Grafana Tempo) |
| Drift | Evidently |
| Frontend | Next.js 14 / TypeScript / Tailwind / Zustand / framer-motion |
| Infra | Docker Compose — postgres + prometheus + grafana + mlflow |

## Key invariants (never break these)

- NO LangGraph, LangChain, LlamaIndex — custom orchestrator only
- NO ORM (SQLAlchemy/Tortoise) — asyncpg + raw SQL only
- NO global mutable state — session store (`api/deps.py`) is the only shared state
- NO `print` / `console.log` in committed code
- Heavy deps (mlflow, evidently, ragas) MUST be lazy-imported inside function bodies
- Every file starts with `from __future__ import annotations`
- Engines/orchestrator stay PURE — no FastAPI imports inside `orchestrator/`

## Directory layout

```
backend/api/            → FastAPI routes + Pydantic models
backend/orchestrator/   → AsyncAgent + tools + memory (no FastAPI imports)
backend/eval/           → benchmark + metrics + CLI harness
backend/ops/            → MLflow + OTel + Evidently
backend/utils/          → config (pydantic-settings) + helpers + exceptions
frontend/src/           → Next.js 14 app (Luminal Void theme)
infra/                  → Docker Compose + Prometheus + Grafana dashboards
.github/workflows/      → eval-gate (blocks on regression) + ci (lint+test+tsc)
```

## Port map

| Service | Port |
|---|---|
| Backend (uvicorn) | 8001 |
| Frontend (Next.js) | 3001 |
| Postgres | 5433 |
| Prometheus | 9090 |
| Grafana | 3030 |
| MLflow | 5050 |

## Week 1 focus (begin here)

1. Expand `eval/data/veris_bench_v1.jsonl` to 30 queries (EN/FR/AR split 15/10/5)
2. Implement `TavilySearchTool.run()` in `orchestrator/tools/search.py`
3. Implement `AsyncAgent._plan()` with a real Anthropic call in `orchestrator/agent.py`

## Decisions log

- 2026-04-25: Scaffolded. asyncio state machine chosen over graph-based (simpler, no framework lock-in, more readable for portfolio).
- 2026-04-25: pgvector reuses nexus Supabase pattern (same connection string, different table prefix `veris_`).
- 2026-04-25: SSE streaming via `fetch()` + `ReadableStream` (not `EventSource`) to support POST body.
- 2026-04-25: `strict: false` in tsconfig — pragmatic for velocity; tighten in W6.

## Commit convention

```
feat(orchestrator): implement _plan step with Anthropic call
fix(eval): handle empty ground_truth_citations gracefully
chore(bench): expand to 30 queries

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```
