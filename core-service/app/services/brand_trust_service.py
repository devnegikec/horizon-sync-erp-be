"""Service layer for Brand Trust Assessment module"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.brand_trust_repository import BrandTrustRepository
from app.schemas.brand_trust import SendReportEmailRequest, StartAssessmentRequest, SubmitAssessmentRequest

logger = logging.getLogger(__name__)

# Score thresholds for letter grades
_GRADE_THRESHOLDS = [
    (90, "A"),
    (75, "B"),
    (60, "C"),
    (45, "D"),
    (0,  "F"),
]


def _letter_grade(score: Decimal) -> str:
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


class BrandTrustService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BrandTrustRepository(db)

    def _paginate(self, total: int, page: int, page_size: int) -> dict:
        total_pages = max(1, (total + page_size - 1) // page_size)
        return {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    # ── Industries ────────────────────────────────────────────────────────────

    def list_industries(self):
        return self.repo.list_industries(active_only=True)

    # ── Questions ─────────────────────────────────────────────────────────────

    def get_questions(self, industry_id: UUID | None = None):
        return self.repo.get_questions(industry_id)

    # ── Start Assessment ──────────────────────────────────────────────────────

    def start_assessment(
        self, data: StartAssessmentRequest, organization_id: UUID, user_id: UUID
    ):
        # Validate industry if provided
        if data.industry_id:
            industry = self.repo.get_industry(data.industry_id)
            if not industry:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="Industry not found.")

        assessment = self.repo.create_assessment({
            "organization_id": organization_id,
            "industry_id": data.industry_id,
            "started_by": user_id,
            "status": "in_progress",
            "notes": data.notes,
        })

        # Attach relevant questions to the response
        questions = self.repo.get_questions(data.industry_id)
        result = self._assessment_dict(assessment)
        result["questions"] = [self._question_dict(q) for q in questions]
        return result

    # ── Submit Assessment ─────────────────────────────────────────────────────

    def submit_assessment(
        self,
        assessment_id: UUID,
        data: SubmitAssessmentRequest,
        organization_id: UUID,
    ):
        assessment = self._get_or_404(assessment_id, organization_id)

        if assessment.status == "submitted":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assessment has already been submitted.",
            )

        # Validate all question IDs exist
        for item in data.answers:
            if not self.repo.get_question(item.question_id):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Question {item.question_id} not found.",
                )

        # Persist answers
        answer_rows = [
            {
                "assessment_id": assessment_id,
                "question_id": item.question_id,
                "answer_value": item.answer_value,
                "answered_at": datetime.now(UTC),
            }
            for item in data.answers
        ]
        self.repo.upsert_answers(assessment_id, answer_rows)

        # Compute score
        overall_score, score_breakdown = self._compute_score(assessment_id, data)

        self.repo.update_assessment(assessment, {
            "status": "submitted",
            "overall_score": overall_score,
            "score_breakdown": score_breakdown,
            "submitted_at": datetime.now(UTC),
        })

        logger.info(
            "[BRAND TRUST] assessment submitted id=%s org=%s score=%.2f",
            assessment_id, organization_id, overall_score,
        )

        result = self._assessment_dict(assessment)
        result["questions"] = []
        return result

    def _compute_score(
        self, assessment_id: UUID, data: SubmitAssessmentRequest
    ) -> tuple[Decimal, dict]:
        """
        Scoring logic:
        - rating questions: value 1-5 → normalised to 0-100 per weight
        - yes_no: yes=100, no=0
        - text / multiple_choice: not scored (weight treated as 0)
        Returns (overall_score 0-100, section_breakdown dict)
        """
        answer_map = {str(a.question_id): a.answer_value for a in data.answers}
        questions = [self.repo.get_question(a.question_id) for a in data.answers]

        section_totals: dict[str, list] = {}  # section → [(weighted_score, weight)]

        for q in questions:
            if q is None:
                continue
            raw = answer_map.get(str(q.id), "")
            weight = float(q.weight or 1.0)

            if q.question_type == "rating":
                try:
                    val = max(1, min(5, int(raw)))
                    normalised = (val - 1) / 4 * 100  # 1→0, 5→100
                except (ValueError, TypeError):
                    normalised = 0.0
            elif q.question_type == "yes_no":
                normalised = 100.0 if str(raw).lower() in ("yes", "true", "1") else 0.0
            else:
                # text / multiple_choice — not scored
                continue

            section_totals.setdefault(q.section, []).append((normalised * weight, weight))

        # Aggregate per section
        section_breakdown: dict[str, float] = {}
        total_weighted = 0.0
        total_weight = 0.0

        for section, pairs in section_totals.items():
            sec_score = sum(s for s, _ in pairs)
            sec_weight = sum(w for _, w in pairs)
            section_breakdown[section] = round(sec_score / sec_weight, 2) if sec_weight else 0.0
            total_weighted += sec_score
            total_weight += sec_weight

        overall = Decimal(str(round(total_weighted / total_weight, 2))) if total_weight else Decimal("0")
        return overall, section_breakdown

    # ── Report ────────────────────────────────────────────────────────────────

    def get_report(self, assessment_id: UUID, organization_id: UUID):
        assessment = self._get_or_404(assessment_id, organization_id)

        if assessment.status == "in_progress":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assessment has not been submitted yet.",
            )

        industry_name = assessment.industry.name if assessment.industry else None
        overall = assessment.overall_score or Decimal("0")
        breakdown = assessment.score_breakdown or {}

        section_scores = [
            {
                "section": section,
                "score": Decimal(str(score)),
                "max_score": Decimal("100"),
                "percentage": Decimal(str(score)),
            }
            for section, score in breakdown.items()
        ]

        answers = self.repo.get_answers(assessment_id)
        answer_details = [
            {
                "question_id": str(a.question_id),
                "question_text": a.question.question_text if a.question else None,
                "section": a.question.section if a.question else None,
                "answer_value": a.answer_value,
            }
            for a in answers
        ]

        return {
            "assessment_id": assessment.id,
            "organization_id": assessment.organization_id,
            "industry_name": industry_name,
            "overall_score": overall,
            "grade": _letter_grade(overall),
            "section_scores": section_scores,
            "submitted_at": assessment.submitted_at,
            "answers": answer_details,
        }

    # ── Send Report Email ─────────────────────────────────────────────────────

    async def send_report_email(
        self,
        assessment_id: UUID,
        req: SendReportEmailRequest,
        organization_id: UUID,
        user_id: UUID,
    ) -> dict:
        assessment = self._get_or_404(assessment_id, organization_id)

        if assessment.status == "in_progress":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot email report for an in-progress assessment.",
            )

        report = self.get_report(assessment_id, organization_id)
        subject = f"Brand Trust Assessment Report — Score: {report['overall_score']} ({report['grade']})"
        body = req.message or (
            f"Please find your Brand Trust Assessment report attached.\n\n"
            f"Overall Score: {report['overall_score']} / 100  (Grade: {report['grade']})\n"
            f"Industry: {report['industry_name'] or 'General'}\n"
            f"Submitted: {report['submitted_at']}"
        )

        # Reuse the communications service
        from app.services.communication_service import CommunicationService
        comm_svc = CommunicationService(self.db)
        result = await comm_svc.send_email(
            to=req.to,
            subject=subject,
            message=body,
            organization_id=organization_id,
            user_id=user_id,
            cc=req.cc,
            doc_type="brand_trust_assessment",
            doc_id=str(assessment_id),
        )

        logger.info(
            "[BRAND TRUST] report email sent assessment=%s to=%s status=%s",
            assessment_id, req.to, result.get("status"),
        )
        return result

    # ── PDF (stub) ────────────────────────────────────────────────────────────

    def get_pdf_url(self, assessment_id: UUID, organization_id: UUID) -> dict:
        """
        Stub: returns a placeholder PDF URL.
        Real implementation would generate a PDF and upload to GCS/S3.
        """
        assessment = self._get_or_404(assessment_id, organization_id)

        if assessment.status == "in_progress":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assessment has not been submitted yet.",
            )

        # If a report_url is already stored, return it
        if assessment.report_url:
            return {"assessment_id": assessment_id, "pdf_url": assessment.report_url}

        # Stub URL — replace with real PDF generation
        stub_url = f"/reports/brand-trust/{assessment_id}.pdf"
        self.repo.update_assessment(assessment, {"report_url": stub_url})

        logger.info("[BRAND TRUST] PDF stub generated assessment=%s", assessment_id)
        return {"assessment_id": assessment_id, "pdf_url": stub_url}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_or_404(self, assessment_id: UUID, organization_id: UUID):
        assessment = self.repo.get_assessment(assessment_id, organization_id)
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Assessment not found.")
        return assessment

    def _assessment_dict(self, a) -> dict:
        return {
            "id": a.id,
            "organization_id": a.organization_id,
            "industry_id": a.industry_id,
            "status": a.status,
            "overall_score": a.overall_score,
            "score_breakdown": a.score_breakdown,
            "report_url": a.report_url,
            "notes": a.notes,
            "submitted_at": a.submitted_at,
            "created_at": a.created_at,
            "questions": [],
        }

    def _question_dict(self, q) -> dict:
        return {
            "id": q.id,
            "industry_id": q.industry_id,
            "section": q.section,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "options": q.options,
            "weight": q.weight,
            "order_index": q.order_index,
        }

    def list_assessments(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ):
        items, total = self.repo.list_assessments(organization_id, page, page_size, status)
        return {
            "assessments": [self._assessment_dict(a) for a in items],
            "pagination": self._paginate(total, page, page_size),
        }
