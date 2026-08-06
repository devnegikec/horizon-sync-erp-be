"""RAG (Retrieval-Augmented Generation) engine for SOP Copilot.

Pipeline:
1. Embed user question
2. Vector similarity search in pgvector (top-k)
3. Optional: keyword BM25 re-ranking fallback
4. Build context window from retrieved chunks
5. Call LLM with system prompt + context + question
6. Extract citations, log to audit table
"""

import logging
import time
from typing import Any, Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.chat_log import ChatLog
from app.models.vector_chunk import VectorChunk
from app.services.embedding import get_embedding_service

logger = logging.getLogger(__name__)

# ── System prompt ────────────────────────────────────────────────────────
_COPILOT_SYSTEM_PROMPT = """You are a Warehouse Operations Assistant.
Answer the operator's question using ONLY the provided SOP context and warehouse data.

Rules:
1. Cite the source document name and section in [brackets] like [SOP: Receiving Procedures, Section 3.2].
2. If the answer requires a system action (e.g., create a put-away exception), output the action in a JSON block.
3. If the answer is not in the context, say "I don't have that information" — do not hallucinate.
4. Keep answers under 150 words unless a detailed procedure is requested.
5. Be concise and action-oriented — warehouse operators are busy.

Context:
{context}
"""


class RAGEngine:
    """Orchestrate retrieval + generation for the SOP Copilot."""

    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.top_k = settings.RAG_TOP_K
        self.similarity_threshold = settings.RAG_SIMILARITY_THRESHOLD

    async def ask(
        self,
        question: str,
        db: Session,
        user_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        warehouse_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Full RAG pipeline: retrieve chunks, generate answer, log audit.

        Returns:
            {
                "answer": str,
                "citations": list[dict],
                "retrieved_chunks": list[dict],
                "model_used": str,
            }
        """
        t_start = time.perf_counter()

        # 1. Embed the question
        question_embedding = await self.embedding_service.embed_single(question)
        if not question_embedding:
            raise RuntimeError("Failed to embed question")

        # 2. Vector similarity search
        t_retrieve_start = time.perf_counter()
        chunks = self._retrieve_chunks(
            db,
            embedding=question_embedding,
            organization_id=organization_id,
            warehouse_id=warehouse_id,
        )
        retrieval_time_ms = (time.perf_counter() - t_retrieve_start) * 1000

        # 3. Build context window
        context_text = self._build_context(chunks)

        # 4. Generate answer via LLM
        t_gen_start = time.perf_counter()
        answer, citations, model_used = await self._generate(question, context_text)
        generation_time_ms = (time.perf_counter() - t_gen_start) * 1000

        total_time_ms = (time.perf_counter() - t_start) * 1000

        # 5. Log audit
        chat_log = ChatLog(
            user_id=user_id,
            organization_id=organization_id,
            warehouse_id=warehouse_id,
            session_id=session_id,
            question=question,
            retrieved_chunks=[
                {
                    "chunk_id": str(c.id),
                    "source_type": c.source_type.value if c.source_type else None,
                    "source_title": c.source_title,
                    "section": c.section,
                    "score": getattr(c, "_score", None),
                    "content_preview": c.content[:200] + "..." if len(c.content) > 200 else c.content,
                }
                for c in chunks
            ],
            retrieval_time_ms=retrieval_time_ms,
            answer=answer,
            model_used=model_used,
            generation_time_ms=generation_time_ms,
            citations=citations,
        )
        db.add(chat_log)
        db.commit()

        logger.info(
            "Copilot answer generated in %.1fms (retrieve=%.1fms, generate=%.1fms) for user=%s",
            total_time_ms, retrieval_time_ms, generation_time_ms, user_id,
        )

        return {
            "answer": answer,
            "citations": citations,
            "retrieved_chunks": chat_log.retrieved_chunks,
            "model_used": model_used,
        }

    def _retrieve_chunks(
        self,
        db: Session,
        embedding: list[float],
        organization_id: Optional[UUID] = None,
        warehouse_id: Optional[UUID] = None,
    ) -> list[VectorChunk]:
        """Run pgvector similarity search with optional RBAC filtering."""
        from sqlalchemy import text

        # Build query with vector distance using <=> operator (cosine distance)
        # Lower distance = more similar
        sql = """
            SELECT
                id, source_type, source_id, source_title, section,
                content, content_hash, chunk_index,
                organization_id, warehouse_id,
                created_at, updated_at,
                embedding <=> :embedding AS distance
            FROM vector_chunks
            WHERE 1=1
        """
        params: dict = {"embedding": str(embedding), "limit": self.top_k * 2}

        if organization_id:
            sql += " AND (organization_id = :org_id OR organization_id IS NULL)"
            params["org_id"] = str(organization_id)
        if warehouse_id:
            sql += " AND (warehouse_id = :wh_id OR warehouse_id IS NULL)"
            params["wh_id"] = str(warehouse_id)

        sql += """
            ORDER BY embedding <=> :embedding
            LIMIT :limit
        """

        result = db.execute(text(sql), params)
        rows = result.mappings().all()

        # Convert rows to VectorChunk objects and filter by threshold
        chunks: list[VectorChunk] = []
        for row in rows:
            if row["distance"] > (1 - self.similarity_threshold):
                continue
            chunk = VectorChunk(
                id=row["id"],
                source_type=row["source_type"],
                source_id=row["source_id"],
                source_title=row["source_title"],
                section=row["section"],
                content=row["content"],
                content_hash=row["content_hash"],
                chunk_index=row["chunk_index"],
                organization_id=row["organization_id"],
                warehouse_id=row["warehouse_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            chunk._score = 1 - float(row["distance"])  # cosine similarity
            chunks.append(chunk)

        return chunks[:self.top_k]

    @staticmethod
    def _build_context(chunks: list[VectorChunk]) -> str:
        """Format retrieved chunks into a context string for the LLM."""
        parts: list[str] = []
        for i, chunk in enumerate(chunks, 1):
            header = f"[{i}]"
            if chunk.source_title:
                header += f" {chunk.source_title}"
            if chunk.section:
                header += f" — {chunk.section}"
            parts.append(f"{header}\n{chunk.content}\n")
        return "\n---\n".join(parts)

    async def _generate(self, question: str, context: str) -> tuple[str, list[dict], str]:
        """Call LLM to generate answer with citations."""
        provider = settings.LLM_PROVIDER.lower()
        system_prompt = _COPILOT_SYSTEM_PROMPT.format(context=context)

        if provider == "openai":
            return await self._generate_openai(system_prompt, question)
        if provider == "anthropic":
            return await self._generate_anthropic(system_prompt, question)
        if provider == "ollama":
            return await self._generate_ollama(system_prompt, question)
        raise ValueError(f"Unsupported LLM provider: {provider}")

    async def _generate_openai(self, system_prompt: str, question: str) -> tuple[str, list[dict], str]:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not configured")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            "temperature": 0.3,
            "max_tokens": 512,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            answer = data["choices"][0]["message"]["content"]

        citations = self._extract_citations(answer)
        return answer, citations, settings.OPENAI_MODEL

    async def _generate_anthropic(self, system_prompt: str, question: str) -> tuple[str, list[dict], str]:
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.ANTHROPIC_MODEL,
            "max_tokens": 512,
            "system": system_prompt,
            "messages": [{"role": "user", "content": question}],
            "temperature": 0.3,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            answer = data["content"][0]["text"]

        citations = self._extract_citations(answer)
        return answer, citations, settings.ANTHROPIC_MODEL

    async def _generate_ollama(self, system_prompt: str, question: str) -> tuple[str, list[dict], str]:
        url = f"{settings.OLLAMA_BASE_URL}/api/chat"
        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            "stream": False,
            "options": {"temperature": 0.3},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            answer = data["message"]["content"]

        citations = self._extract_citations(answer)
        return answer, citations, settings.OLLAMA_MODEL

    @staticmethod
    def _extract_citations(answer: str) -> list[dict]:
        """Parse [bracket] citations from the answer text."""
        import re
        citations = []
        for match in re.finditer(r"\[([^\]]+)\]", answer):
            cite_text = match.group(1).strip()
            if ":" in cite_text:
                parts = cite_text.split(":", 1)
                citations.append({"source": parts[0].strip(), "section": parts[1].strip()})
            else:
                citations.append({"source": cite_text, "section": ""})
        return citations


def get_rag_engine() -> RAGEngine:
    """Factory: return a RAGEngine instance."""
    return RAGEngine()
