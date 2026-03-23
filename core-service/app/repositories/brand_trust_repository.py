"""Repository for Brand Trust Assessment module"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.brand_trust import (
    BrandIndustry,
    BrandTrustAnswer,
    BrandTrustAssessment,
    BrandTrustQuestion,
)


class BrandTrustRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Industries ────────────────────────────────────────────────────────────

    def list_industries(self, active_only: bool = True) -> list[BrandIndustry]:
        q = self.db.query(BrandIndustry)
        if active_only:
            q = q.filter(BrandIndustry.is_active.is_(True))
        return q.order_by(BrandIndustry.name).all()

    def get_industry(self, industry_id: UUID) -> BrandIndustry | None:
        return self.db.query(BrandIndustry).filter(BrandIndustry.id == industry_id).first()

    # ── Questions ─────────────────────────────────────────────────────────────

    def get_questions(self, industry_id: UUID | None = None) -> list[BrandTrustQuestion]:
        """Return active questions for an industry + universal questions (industry_id IS NULL)."""
        q = self.db.query(BrandTrustQuestion).filter(
            BrandTrustQuestion.is_active.is_(True)
        )
        if industry_id:
            q = q.filter(
                (BrandTrustQuestion.industry_id == industry_id)
                | BrandTrustQuestion.industry_id.is_(None)
            )
        else:
            q = q.filter(BrandTrustQuestion.industry_id.is_(None))
        return q.order_by(BrandTrustQuestion.order_index).all()

    def get_question(self, question_id: UUID) -> BrandTrustQuestion | None:
        return self.db.query(BrandTrustQuestion).filter(
            BrandTrustQuestion.id == question_id
        ).first()

    # ── Assessments ───────────────────────────────────────────────────────────

    def create_assessment(self, data: dict) -> BrandTrustAssessment:
        assessment = BrandTrustAssessment(**data)
        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)
        return assessment

    def get_assessment(self, assessment_id: UUID, organization_id: UUID) -> BrandTrustAssessment | None:
        return (
            self.db.query(BrandTrustAssessment)
            .filter(
                BrandTrustAssessment.id == assessment_id,
                BrandTrustAssessment.organization_id == organization_id,
            )
            .first()
        )

    def list_assessments(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[BrandTrustAssessment], int]:
        q = self.db.query(BrandTrustAssessment).filter(
            BrandTrustAssessment.organization_id == organization_id
        )
        if status:
            q = q.filter(BrandTrustAssessment.status == status)
        total = q.count()
        items = (
            q.order_by(BrandTrustAssessment.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def update_assessment(self, assessment: BrandTrustAssessment, data: dict) -> BrandTrustAssessment:
        for k, v in data.items():
            setattr(assessment, k, v)
        self.db.commit()
        self.db.refresh(assessment)
        return assessment

    # ── Answers ───────────────────────────────────────────────────────────────

    def upsert_answers(self, assessment_id: UUID, answers: list[dict]) -> None:
        """Delete existing answers for this assessment and insert fresh ones."""
        self.db.query(BrandTrustAnswer).filter(
            BrandTrustAnswer.assessment_id == assessment_id
        ).delete()
        for a in answers:
            self.db.add(BrandTrustAnswer(**a))
        self.db.commit()

    def get_answers(self, assessment_id: UUID) -> list[BrandTrustAnswer]:
        return (
            self.db.query(BrandTrustAnswer)
            .filter(BrandTrustAnswer.assessment_id == assessment_id)
            .all()
        )
