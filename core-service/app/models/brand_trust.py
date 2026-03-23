"""Brand Trust Assessment models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class BrandIndustry(Base):
    __tablename__ = "brand_industries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    questions = relationship("BrandTrustQuestion", back_populates="industry")
    assessments = relationship("BrandTrustAssessment", back_populates="industry")


class BrandTrustQuestion(Base):
    __tablename__ = "brand_trust_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    industry_id = Column(UUID(as_uuid=True), ForeignKey("brand_industries.id"), nullable=True)
    section = Column(String(100), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(20), default="rating")  # rating|yes_no|text|multiple_choice
    options = Column(JSONB, nullable=True)
    weight = Column(Numeric(4, 2), default=1.0)
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    industry = relationship("BrandIndustry", back_populates="questions")
    answers = relationship("BrandTrustAnswer", back_populates="question")


class BrandTrustAssessment(Base):
    __tablename__ = "brand_trust_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    industry_id = Column(UUID(as_uuid=True), ForeignKey("brand_industries.id"), nullable=True)
    started_by = Column(UUID(as_uuid=True), nullable=True)
    status = Column(String(20), default="in_progress")  # in_progress|submitted|scored
    overall_score = Column(Numeric(5, 2), nullable=True)
    score_breakdown = Column(JSONB, nullable=True)
    report_url = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC),
                        onupdate=lambda: datetime.now(UTC))

    industry = relationship("BrandIndustry", back_populates="assessments")
    answers = relationship("BrandTrustAnswer", back_populates="assessment",
                           cascade="all, delete-orphan")


class BrandTrustAnswer(Base):
    __tablename__ = "brand_trust_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id = Column(UUID(as_uuid=True),
                           ForeignKey("brand_trust_assessments.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    question_id = Column(UUID(as_uuid=True),
                         ForeignKey("brand_trust_questions.id"), nullable=False)
    answer_value = Column(Text, nullable=True)
    answered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    assessment = relationship("BrandTrustAssessment", back_populates="answers")
    question = relationship("BrandTrustQuestion", back_populates="answers")
