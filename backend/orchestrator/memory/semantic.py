from __future__ import annotations

from typing import Any

import asyncpg

from utils.helpers import get_logger

logger = get_logger(__name__)

_DDL = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS semantic_memory (
    id         TEXT        PRIMARY KEY,
    text       TEXT        NOT NULL,
    embedding  vector(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_semantic_hnsw
    ON semantic_memory USING hnsw (embedding vector_cosine_ops);
"""

_MODEL_NAME = "all-MiniLM-L6-v2"


class SemanticMemory:
    """pgvector-backed semantic similarity store (384-dim MiniLM embeddings)."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None
        self._model = None  # lazy SentenceTransformer

    async def init(self) -> None:
        from pgvector.asyncpg import register_vector
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(_MODEL_NAME)

        async def _init_conn(conn: asyncpg.Connection) -> None:
            await register_vector(conn)

        self._pool = await asyncpg.create_pool(
            self._dsn, min_size=2, max_size=10, init=_init_conn
        )
        async with self._pool.acquire() as conn:
            await conn.execute(_DDL)
        logger.info("SemanticMemory: pool ready (dim=384, model=%s)", _MODEL_NAME)

    def _embed(self, text: str) -> list[float]:
        assert self._model is not None, "call init() first"
        return self._model.encode(text, normalize_embeddings=True).tolist()

    async def upsert(self, doc_id: str, text: str) -> None:
        assert self._pool is not None, "call init() first"
        embedding = self._embed(text)
        await self._pool.execute(
            """
            INSERT INTO semantic_memory (id, text, embedding)
            VALUES ($1, $2, $3)
            ON CONFLICT (id) DO UPDATE
                SET text = EXCLUDED.text, embedding = EXCLUDED.embedding
            """,
            doc_id,
            text,
            embedding,
        )

    async def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        assert self._pool is not None, "call init() first"
        embedding = self._embed(query)
        rows = await self._pool.fetch(
            """
            SELECT id, text, 1 - (embedding <=> $1) AS score
            FROM semantic_memory
            ORDER BY embedding <=> $1
            LIMIT $2
            """,
            embedding,
            top_k,
        )
        return [{"id": r["id"], "text": r["text"], "score": float(r["score"])} for r in rows]

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            logger.info("SemanticMemory: pool closed")
