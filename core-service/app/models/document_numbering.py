"""Document numbering series configuration and sequence counter.

Used for configurable document numbers (Payment, Invoice, Quotation, Sales Order,
Pick List, Delivery Note, Purchase Order, RFQ, Material Request, Purchase Receipt).
Prefix and format are defined per organization and document type; sequence is
stored per (org, document_type, year) for atomic next-number generation.
"""

import uuid

from sqlalchemy import Boolean, Column, Integer, String, UniqueConstraint

from app.database import Base
from app.models.types import UUID

# Document types aligned with frontend Document Numbering Series (Settings)
DOCUMENT_TYPES = [
    "quotation",
    "sales_order",
    "pick_list",
    "invoice",
    "purchase_order",
    "rfq",
    "material_request",
    "delivery_note",
    "purchase_receipt",
    "payment",
    "item",
    "item_group",
    "stock_entry",
    "stock_reconciliation",
    "journal_entry",
]

# Default prefix per document type (used when seeding new org config)
DEFAULT_PREFIXES = {
    "quotation": "QT",
    "sales_order": "SO",
    "pick_list": "PL",
    "invoice": "INV",
    "purchase_order": "PO",
    "rfq": "RFQ",
    "material_request": "MR",
    "delivery_note": "DN",
    "purchase_receipt": "PR",
    "payment": "RCP",
    "item": "ITM",
    "item_group": "IG",
    "stock_entry": "SE",
    "stock_reconciliation": "SREC",
    "journal_entry": "JE",
}


class DocumentNumberingConfig(Base):
    """Per-organization, per-document-type config: prefix, padding, include_year."""

    __tablename__ = "document_numbering_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    document_type = Column(String(50), nullable=False, index=True)
    prefix = Column(String(20), nullable=False)
    padding = Column(Integer, nullable=False, default=5)
    include_year = Column(Boolean, nullable=False, default=True)
    separator = Column(String(5), nullable=False, default="-")

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "document_type", name="uq_doc_numbering_org_type"
        ),
    )


class DocumentSequenceCounter(Base):
    """Atomic counter per (organization, document_type, year). Year is NULL when include_year=False."""

    __tablename__ = "document_sequence_counter"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    document_type = Column(String(50), nullable=False, index=True)
    sequence_year = Column(Integer, nullable=True)
    next_number = Column(Integer, nullable=False, default=1)

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "document_type",
            "sequence_year",
            name="uq_doc_sequence_org_type_year",
        ),
    )
