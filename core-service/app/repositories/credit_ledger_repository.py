"""Database access for credit batches, the append-only ledger and top-ups."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.subscription import (
    CreditBatch,
    CreditLedger,
    GenerationOperation,
    TopupOrder,
    TopupQuote,
)

ZERO = Decimal("0.000000")


def _available_expr():
    return (
        CreditBatch.granted_qty
        - CreditBatch.consumed_qty
        - CreditBatch.reserved_qty
        - CreditBatch.expired_qty
        - CreditBatch.reversed_qty
    )


class CreditLedgerRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Batches ─────────────────────────────────────────────────────────────

    def get_batch_by_source(
        self,
        organization_id: UUID,
        source_type: str,
        source_id: UUID | None,
    ) -> CreditBatch | None:
        query = self.db.query(CreditBatch).filter(
            CreditBatch.organization_id == organization_id,
            CreditBatch.source_type == source_type,
        )
        if source_id is None:
            query = query.filter(CreditBatch.source_id.is_(None))
        else:
            query = query.filter(CreditBatch.source_id == source_id)
        return query.first()

    def list_batches(
        self,
        organization_id: UUID,
        *,
        status: str | None = None,
        expiring_before: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[CreditBatch], int]:
        query = self.db.query(CreditBatch).filter(
            CreditBatch.organization_id == organization_id
        )
        if status:
            query = query.filter(CreditBatch.status == status)
        if expiring_before:
            query = query.filter(CreditBatch.expires_at <= expiring_before)
        total = query.count()
        items = (
            query.order_by(CreditBatch.expires_at.asc(), CreditBatch.issued_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def lock_eligible_batches(
        self, organization_id: UUID, as_of: datetime | None = None
    ) -> list[CreditBatch]:
        """FEFO order, locked for the duration of the transaction."""
        as_of = as_of or datetime.now(UTC)
        return (
            self.db.query(CreditBatch)
            .filter(
                CreditBatch.organization_id == organization_id,
                CreditBatch.status == "active",
                CreditBatch.expires_at > as_of,
                _available_expr() > 0,
            )
            .order_by(CreditBatch.expires_at.asc(), CreditBatch.issued_at.asc())
            .with_for_update()
            .all()
        )

    def create_batch(self, data: dict) -> CreditBatch:
        batch = CreditBatch(**data)
        self.db.add(batch)
        self.db.flush()
        return batch

    # ── Ledger ──────────────────────────────────────────────────────────────

    def add_ledger(self, data: dict) -> CreditLedger:
        entry = CreditLedger(**data)
        self.db.add(entry)
        self.db.flush()
        return entry

    def get_ledger_by_idempotency(
        self, organization_id: UUID, idempotency_key: str
    ) -> CreditLedger | None:
        return (
            self.db.query(CreditLedger)
            .filter(
                CreditLedger.organization_id == organization_id,
                CreditLedger.idempotency_key == idempotency_key,
            )
            .first()
        )

    def list_ledger(
        self,
        organization_id: UUID,
        *,
        entry_type: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        operation_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[CreditLedger], int]:
        query = self.db.query(CreditLedger).filter(
            CreditLedger.organization_id == organization_id
        )
        if entry_type:
            query = query.filter(CreditLedger.type == entry_type)
        if from_date:
            query = query.filter(CreditLedger.occurred_at >= from_date)
        if to_date:
            query = query.filter(CreditLedger.occurred_at <= to_date)
        if operation_id:
            query = query.filter(CreditLedger.operation_id == operation_id)
        total = query.count()
        items = (
            query.order_by(CreditLedger.occurred_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def iter_ledger(
        self,
        organization_id: UUID,
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        chunk_size: int = 1000,
    ) -> Iterator[CreditLedger]:
        """Stream every matching entry (no silent export cap)."""
        query = self.db.query(CreditLedger).filter(
            CreditLedger.organization_id == organization_id
        )
        if from_date:
            query = query.filter(CreditLedger.occurred_at >= from_date)
        if to_date:
            query = query.filter(CreditLedger.occurred_at <= to_date)
        query = query.order_by(CreditLedger.occurred_at.desc())
        yield from query.yield_per(chunk_size)

    # ── Aggregates ──────────────────────────────────────────────────────────

    def sum_available(
        self, organization_id: UUID, as_of: datetime | None = None
    ) -> Decimal:
        as_of = as_of or datetime.now(UTC)
        value = (
            self.db.query(func.coalesce(func.sum(_available_expr()), 0))
            .filter(
                CreditBatch.organization_id == organization_id,
                CreditBatch.status == "active",
                CreditBatch.expires_at > as_of,
            )
            .scalar()
        )
        return Decimal(value or 0)

    def sum_reserved(self, organization_id: UUID) -> Decimal:
        value = (
            self.db.query(func.coalesce(func.sum(CreditBatch.reserved_qty), 0))
            .filter(CreditBatch.organization_id == organization_id)
            .scalar()
        )
        return Decimal(value or 0)

    def used_since(self, organization_id: UUID, since: datetime) -> Decimal:
        value = (
            self.db.query(func.coalesce(func.sum(GenerationOperation.debit_qty), 0))
            .filter(
                GenerationOperation.organization_id == organization_id,
                GenerationOperation.status == "committed",
                GenerationOperation.updated_at >= since,
            )
            .scalar()
        )
        return Decimal(value or 0)

    def expiring_between(
        self,
        organization_id: UUID,
        start: datetime,
        end: datetime,
    ) -> Decimal:
        value = (
            self.db.query(func.coalesce(func.sum(_available_expr()), 0))
            .filter(
                CreditBatch.organization_id == organization_id,
                CreditBatch.status == "active",
                CreditBatch.expires_at > start,
                CreditBatch.expires_at <= end,
            )
            .scalar()
        )
        return Decimal(value or 0)

    def earliest_expiring_batch(
        self, organization_id: UUID, as_of: datetime | None = None
    ) -> CreditBatch | None:
        as_of = as_of or datetime.now(UTC)
        return (
            self.db.query(CreditBatch)
            .filter(
                CreditBatch.organization_id == organization_id,
                CreditBatch.status == "active",
                CreditBatch.expires_at > as_of,
                _available_expr() > 0,
            )
            .order_by(CreditBatch.expires_at.asc())
            .first()
        )

    def list_expiring_batches(
        self, organization_id: UUID, as_of: datetime, until: datetime
    ) -> list[CreditBatch]:
        return (
            self.db.query(CreditBatch)
            .filter(
                CreditBatch.organization_id == organization_id,
                CreditBatch.status == "active",
                CreditBatch.expires_at > as_of,
                CreditBatch.expires_at <= until,
                _available_expr() > 0,
            )
            .order_by(CreditBatch.expires_at.asc())
            .all()
        )

    def list_expired_candidates(self, as_of: datetime) -> list[CreditBatch]:
        return (
            self.db.query(CreditBatch)
            .filter(
                CreditBatch.status == "active",
                CreditBatch.expires_at <= as_of,
                _available_expr() > 0,
            )
            .with_for_update()
            .all()
        )

    # ── Generation operations ───────────────────────────────────────────────

    def get_operation_by_key(
        self, organization_id: UUID, operation_key: str, *, for_update: bool = False
    ) -> GenerationOperation | None:
        query = self.db.query(GenerationOperation).filter(
            GenerationOperation.organization_id == organization_id,
            GenerationOperation.operation_key == operation_key,
        )
        if for_update:
            query = query.with_for_update()
        return query.first()

    def get_operation(
        self, organization_id: UUID, operation_id: UUID, *, for_update: bool = False
    ) -> GenerationOperation | None:
        query = self.db.query(GenerationOperation).filter(
            GenerationOperation.organization_id == organization_id,
            GenerationOperation.id == operation_id,
        )
        if for_update:
            query = query.with_for_update()
        return query.first()

    def create_operation(self, data: dict) -> GenerationOperation:
        operation = GenerationOperation(**data)
        self.db.add(operation)
        self.db.flush()
        return operation

    # ── Top-ups ─────────────────────────────────────────────────────────────

    def create_quote(self, data: dict) -> TopupQuote:
        quote = TopupQuote(**data)
        self.db.add(quote)
        self.db.flush()
        return quote

    def get_quote(
        self, organization_id: UUID, quote_id: UUID, *, for_update: bool = False
    ) -> TopupQuote | None:
        query = self.db.query(TopupQuote).filter(
            TopupQuote.organization_id == organization_id,
            TopupQuote.id == quote_id,
        )
        if for_update:
            query = query.with_for_update()
        return query.first()

    def get_order_by_idempotency(
        self, organization_id: UUID, idempotency_key: str
    ) -> TopupOrder | None:
        return (
            self.db.query(TopupOrder)
            .filter(
                TopupOrder.organization_id == organization_id,
                TopupOrder.idempotency_key == idempotency_key,
            )
            .first()
        )

    def create_order(self, data: dict) -> TopupOrder:
        order = TopupOrder(**data)
        self.db.add(order)
        self.db.flush()
        return order

    def get_order(self, organization_id: UUID, order_id: UUID) -> TopupOrder | None:
        return (
            self.db.query(TopupOrder)
            .filter(
                TopupOrder.organization_id == organization_id,
                TopupOrder.id == order_id,
            )
            .first()
        )

    # ── Reporting ───────────────────────────────────────────────────────────

    def organizations_with_credit(self) -> list[UUID]:
        rows = (
            self.db.query(CreditBatch.organization_id)
            .filter(CreditBatch.status == "active")
            .distinct()
            .all()
        )
        return [row[0] for row in rows]

    def paid_invoices_without_batch(self, limit: int = 100) -> list[tuple]:
        """Invoices marked paid but missing a plan credit batch."""
        from app.models.invoice import Invoice

        return (
            self.db.query(Invoice.id, Invoice.organization_id, Invoice.invoice_no)
            .outerjoin(
                CreditBatch,
                (CreditBatch.source_id == Invoice.id)
                & (CreditBatch.source_type == "invoice_plan"),
            )
            .filter(
                Invoice.invoice_type == "subscription",
                Invoice.status == "paid",
                CreditBatch.id.is_(None),
            )
            .limit(limit)
            .all()
        )

    def grants_without_payment(self, limit: int = 100) -> list[tuple]:
        """Plan grants whose source invoice is missing or not settled."""
        from app.models.invoice import Invoice

        return (
            self.db.query(
                CreditBatch.id,
                CreditBatch.organization_id,
                CreditBatch.source_id,
                Invoice.invoice_no,
                Invoice.status,
            )
            .outerjoin(Invoice, Invoice.id == CreditBatch.source_id)
            .filter(
                CreditBatch.source_type == "invoice_plan",
                or_(Invoice.id.is_(None), Invoice.status != "paid"),
            )
            .limit(limit)
            .all()
        )

    def stuck_reservations(
        self, as_of: datetime, limit: int = 100
    ) -> list[GenerationOperation]:
        return (
            self.db.query(GenerationOperation)
            .filter(
                GenerationOperation.status == "reserved",
                GenerationOperation.reserved_until.isnot(None),
                GenerationOperation.reserved_until < as_of,
            )
            .limit(limit)
            .all()
        )

    def invoice_exposure(self, organization_id: UUID) -> tuple[int, Decimal]:
        """(overdue invoice count, outstanding amount) for account invoices."""
        from app.models.invoice import Invoice

        base = self.db.query(Invoice).filter(
            Invoice.organization_id == organization_id,
            Invoice.invoice_type.in_(("subscription", "setup_fee", "overage", "addon")),
            Invoice.status != "void",
        )
        overdue = base.filter(
            Invoice.status == "overdue", Invoice.outstanding_amount > 0
        ).count()
        outstanding = (
            base.with_entities(
                func.coalesce(func.sum(Invoice.outstanding_amount), 0)
            ).scalar()
            or 0
        )
        return overdue, Decimal(outstanding)

    def expiring_window(self, as_of: datetime, days: int) -> datetime:
        return as_of + timedelta(days=days)
