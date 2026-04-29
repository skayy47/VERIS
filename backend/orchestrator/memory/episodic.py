from __future__ import annotations

import json
from typing import Any

import asyncpg

from utils.helpers import get_logger

logger = get_logger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS episodic_memory (
    id         BIGSERIAL    PRIMARY KEY,
    session_id TEXT         NOT NULL,
    query      TEXT         NOT NULL,
    language   TEXT         NOT NULL DEFAULT 'en',
    answer     TEXT,
    citations  JSONB,
    metrics    JSONB,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_episodic_session
    ON episodic_memory (session_id);
"""


class EpisodicMemory:
    """Postgres-backed per-session interaction log."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def init(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn, min_size=2, max_size=10)
        async with self._pool.acquire() as conn:
            await conn.execute(_DDL)
        logger.info("EpisodicMemory: pool ready")

    async def store(
        self,
        session_id: str,
        query: str,
        language: str,
        answer: str,
        citations: list[dict[str, Any]],
        metrics: dict[str, Any],
    ) -> int:
        assert self._pool is not None, "call init() first"
        row = await self._pool.fetchrow(
            """
            INSERT INTO episodic_memory
                (session_id, query, language, answer, citations, metrics)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb)
            RETURNING id
            """,
            session_id,
            query,
            language,
            answer,
            json.dumps(citations),
            json.dumps(metrics),
        )
        return row["id"]

    async def retrieve_recent(
        self, session_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        assert self._pool is not None, "call init() first"
        rows = await self._pool.fetch(
            """
            SELECT id, session_id, query, language, answer, citations, metrics, created_at
            FROM episodic_memory
            WHERE session_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            session_id,
            limit,
        )
        return [dict(r) for r in rows]

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            logger.info("EpisodicMemory: pool closed")
