"""
Configurable document number generation.

Uses document_numbering_config (prefix, padding, include_year) and
document_sequence_counter for atomic next-number per (org, document_type, year).
Aligns with Settings > Document Numbering Series; add new document types to
DOCUMENT_TYPES and DEFAULT_PREFIXES in app.models.document_numbering.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.document_numbering import (
    DEFAULT_PREFIXES,
    DOCUMENT_TYPES,
    DocumentNumberingConfig,
    DocumentSequenceCounter,
)


class DocumentNumberingService:
    """Generate next document number atomically from configurable series."""

    def __init__(self, db: Session):
        self.db = db

    def get_next_number(
        self,
        organization_id: UUID,
        document_type: str,
        reference_date: datetime | None = None,
    ) -> str:
        """
        Return the next document number for the given org and document type.
        Thread-safe; uses DB counter. Format: {prefix}[{-year}]{separator}{seq:0pad}.

        Args:
            organization_id: Organization UUID
            document_type: One of DOCUMENT_TYPES (quotation, sales_order, payment, etc.)
            reference_date: Date used for year when include_year=True (default: now)

        Returns:
            e.g. "RCP-2026-00001", "INV-2026-00042"
        """
        if document_type not in DOCUMENT_TYPES:
            raise ValidationError(
                f"Unknown document_type '{document_type}'. "
                f"Must be one of: {', '.join(DOCUMENT_TYPES)}"
            )
        config = self._get_or_create_config(organization_id, document_type)
        reference_date = reference_date or datetime.now()
        year = reference_date.year
        sequence_year = year if config.include_year else None

        next_num = self._get_next_sequence_atomic(
            organization_id, document_type, sequence_year
        )

        parts = [config.prefix.strip()]
        if config.include_year:
            parts.append(str(year))
        parts.append(str(next_num).zfill(config.padding))
        return config.separator.join(parts)

    def _get_or_create_config(
        self, organization_id: UUID, document_type: str
    ) -> DocumentNumberingConfig:
        config = (
            self.db.query(DocumentNumberingConfig)
            .filter(
                DocumentNumberingConfig.organization_id == organization_id,
                DocumentNumberingConfig.document_type == document_type,
            )
            .first()
        )
        if config:
            return config
        prefix = DEFAULT_PREFIXES.get(document_type, document_type.upper()[:4])
        config = DocumentNumberingConfig(
            organization_id=organization_id,
            document_type=document_type,
            prefix=prefix,
            padding=5,
            include_year=True,
            separator="-",
        )
        self.db.add(config)
        self.db.flush()
        return config

    def _get_next_sequence_atomic(
        self, organization_id: UUID, document_type: str, sequence_year: int | None
    ) -> int:
        """Increment and return next_number for (org, document_type, year)."""
        from sqlalchemy.dialects.postgresql import insert

        stmt = insert(DocumentSequenceCounter).values(
            organization_id=organization_id,
            document_type=document_type,
            sequence_year=sequence_year,
            next_number=1,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["organization_id", "document_type", "sequence_year"],
            set_={"next_number": DocumentSequenceCounter.next_number + 1},
        )
        result = self.db.execute(stmt.returning(DocumentSequenceCounter.next_number))
        return result.scalar_one()

    def list_config(self, organization_id: UUID) -> list[dict]:
        """Return all document numbering config for an org (for Settings UI)."""
        configs = (
            self.db.query(DocumentNumberingConfig)
            .filter(DocumentNumberingConfig.organization_id == organization_id)
            .all()
        )
        by_type = {c.document_type: c for c in configs}
        out = []
        for doc_type in DOCUMENT_TYPES:
            c = by_type.get(doc_type)
            out.append(
                {
                    "document_type": doc_type,
                    "prefix": c.prefix
                    if c
                    else DEFAULT_PREFIXES.get(doc_type, doc_type.upper()[:4]),
                    "padding": c.padding if c else 5,
                    "include_year": c.include_year if c else True,
                    "separator": c.separator if c else "-",
                }
            )
        return out

    def update_config(
        self,
        organization_id: UUID,
        document_type: str,
        prefix: str | None = None,
        padding: int | None = None,
        include_year: bool | None = None,
        separator: str | None = None,
    ) -> dict:
        """Update one document type config (from Settings UI)."""
        if document_type not in DOCUMENT_TYPES:
            raise ValidationError(f"Unknown document_type '{document_type}'")
        config = self._get_or_create_config(organization_id, document_type)
        if prefix is not None:
            config.prefix = prefix.strip() or DEFAULT_PREFIXES.get(document_type, "DOC")
        if padding is not None:
            config.padding = max(1, min(10, padding))
        if include_year is not None:
            config.include_year = include_year
        if separator is not None:
            config.separator = separator or "-"
        self.db.flush()
        return {
            "document_type": config.document_type,
            "prefix": config.prefix,
            "padding": config.padding,
            "include_year": config.include_year,
            "separator": config.separator,
        }
