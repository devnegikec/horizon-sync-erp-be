"""SOP Copilot API endpoints for ai-service.

RAG-powered chat assistant grounded in warehouse SOPs and knowledge base.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.rag_engine import get_rag_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/copilot", tags=["sop-copilot"])


# ── Schemas ──────────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000, description="Operator's question")
    user_id: Optional[UUID] = Field(None, description="Authenticated user ID")
    organization_id: Optional[UUID] = Field(None, description="Organization scope filter")
    warehouse_id: Optional[UUID] = Field(None, description="Warehouse scope filter")
    session_id: Optional[str] = Field(None, description="Chat session / thread ID")


class Citation(BaseModel):
    source: str
    section: str


class RetrievedChunk(BaseModel):
    chunk_id: str
    source_type: Optional[str]
    source_title: Optional[str]
    section: Optional[str]
    score: Optional[float]
    content_preview: str


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    retrieved_chunks: list[RetrievedChunk]
    model_used: str


class ChatHistoryEntry(BaseModel):
    id: UUID
    question: str
    answer: str
    model_used: Optional[str]
    created_at: str


class ChatHistoryResponse(BaseModel):
    items: list[ChatHistoryEntry]
    total: int


# ── Endpoints ──────────────────────────────────────────────────────────────
@router.post(
    "/ask",
    response_model=AskResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask the SOP Copilot a question",
)
async def copilot_ask(
    request: AskRequest = Body(...),
    db: Session = Depends(get_db),
):
    """Ask a question and get a grounded answer from the knowledge base.

    The response includes citations to source SOPs / documents.
    Every question is logged for compliance audit.
    """
    if not request.question or len(request.question.strip()) < 3:
        raise HTTPException(status_code=400, detail="Question must be at least 3 characters")

    rag_engine = get_rag_engine()
    try:
        result = await rag_engine.ask(
            question=request.question.strip(),
            db=db,
            user_id=request.user_id,
            organization_id=request.organization_id,
            warehouse_id=request.warehouse_id,
            session_id=request.session_id,
        )
    except Exception as e:
        logger.exception("Copilot ask failed")
        raise HTTPException(status_code=500, detail=f"Copilot error: {e}")

    return AskResponse(
        answer=result["answer"],
        citations=[Citation(**c) for c in result["citations"]],
        retrieved_chunks=[RetrievedChunk(**c) for c in result["retrieved_chunks"]],
        model_used=result["model_used"],
    )


@router.get("/history", response_model=ChatHistoryResponse)
async def copilot_history(
    user_id: Optional[UUID] = Query(None),
    organization_id: Optional[UUID] = Query(None),
    warehouse_id: Optional[UUID] = Query(None),
    session_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Get audit history of copilot interactions.

    Filter by user, org, warehouse, or session. Default limit 20.
    """
    from app.models.chat_log import ChatLog

    query = db.query(ChatLog)
    if user_id:
        query = query.filter(ChatLog.user_id == user_id)
    if organization_id:
        query = query.filter(ChatLog.organization_id == organization_id)
    if warehouse_id:
        query = query.filter(ChatLog.warehouse_id == warehouse_id)
    if session_id:
        query = query.filter(ChatLog.session_id == session_id)

    total = query.count()
    logs = (
        query.order_by(ChatLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return ChatHistoryResponse(
        items=[
            ChatHistoryEntry(
                id=log.id,
                question=log.question,
                answer=log.answer or "",
                model_used=log.model_used,
                created_at=log.created_at.isoformat() if log.created_at else "",
            )
            for log in logs
        ],
        total=total,
    )
