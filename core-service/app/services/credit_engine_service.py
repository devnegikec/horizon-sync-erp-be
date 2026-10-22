"""Credit engine: FEFO reservation, consumption, expiry and adjustments."""

from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.invoice import Invoice
from app.models.subscription import (
    CREDIT_BATCH_STATUS_ACTIVE,
    CREDIT_BATCH_STATUS_EXHAUSTED,
    CREDIT_BATCH_STATUS_EXPIRED,
    GENERATION_STATUS_COMMITTED,
    GENERATION_STATUS_RELEASED,
    GENERATION_STATUS_RESERVED,
    LEDGER_ADJUST_NEGATIVE,
    LEDGER_ADJUST_POSITIVE,
    LEDGER_CONSUME,
    LEDGER_EXPIRE,
    LEDGER_GRANT,
    LEDGER_RELEASE,
    LEDGER_RESERVE,
    SUBSCRIPTION_STATUS_ACTIVE,
    SUBSCRIPTION_STATUS_OVERDUE,
)
from app.repositories.credit_ledger_repository import CreditLedgerRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.razorpay_service import RazorpayService
from app.services.subscription_service import add_months

SIX = Decimal("0.000001")
CENT = Decimal("0.01")

#: Fallback unit price when a plan version does not price its credits.
DEFAULT_TOPUP_UNIT_PRICE = Decimal("0.05")

RESERVATION_TTL_MINUTES = 15
TOPUP_QUOTE_TTL_MINUTES = 15
CREDIT_VALIDITY_MONTHS = 12

RESERVABLE_STATUSES = (SUBSCRIPTION_STATUS_ACTIVE, SUBSCRIPTION_STATUS_OVERDUE)


def q6(value: Decimal | int) -> Decimal:
    return Decimal(value).quantize(SIX, rounding=ROUND_HALF_UP)


def q2(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _aware(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat them as UTC."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def credit_error(code: str, message: str, http_status: int, **context):
    detail = {"code": code, "message": message}
    if context:
        detail["context"] = context
    return HTTPException(status_code=http_status, detail=detail)


class CreditEngineService:
    def __init__(self, db: Session):
        self.db = db
        self.credit_repo = CreditLedgerRepository(db)
        self.subscription_repo = SubscriptionRepository(db)

    # ── Contract lookup ─────────────────────────────────────────────────────

    def _contract(self, organization_id: UUID):
        subscription = self.subscription_repo.get_subscription(organization_id)
        if subscription is None:
            raise credit_error(
                "NO_ACTIVE_SUBSCRIPTION",
                "No subscription is configured for this organization",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        applied_pending = False
        if subscription.pending_plan_version_id:
            due = _aware(subscription.pending_effective_from)
            if due is not None and due <= datetime.now(UTC):
                pending = self.subscription_repo.get_version(
                    subscription.pending_plan_version_id
                )
                if pending is not None:
                    subscription.plan_version_id = pending.id
                    subscription.billing_cadence = pending.billing_cadence
                    applied_pending = True
                subscription.pending_plan_version_id = None
                subscription.pending_effective_from = None
                self.db.commit()
        version = self.subscription_repo.get_version(subscription.plan_version_id)
        if version is None:
            raise credit_error(
                "NO_ACTIVE_SUBSCRIPTION",
                "Subscription has no plan version",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return subscription, version, applied_pending

    @staticmethod
    def _assert_started(version, allow_early: bool = False) -> None:
        if allow_early:
            return
        start = _aware(version.effective_from)
        if start is not None and start > datetime.now(UTC):
            raise credit_error(
                "SUBSCRIPTION_NOT_STARTED",
                "The contract version is not effective yet",
                status.HTTP_402_PAYMENT_REQUIRED,
                effective_from=start.isoformat(),
            )

    def current_weight(self, organization_id: UUID) -> Decimal:
        _, version, _ = self._contract(organization_id)
        return q6(version.id_weight)

    # ── Rating ──────────────────────────────────────────────────────────────

    def rate(self, organization_id: UUID, id_count: int) -> dict:
        subscription, version, applied_pending = self._contract(organization_id)
        if subscription.status not in RESERVABLE_STATUSES:
            raise credit_error(
                "SUBSCRIPTION_INACTIVE",
                f"Subscription is {subscription.status}; issuance is paused",
                status.HTTP_402_PAYMENT_REQUIRED,
            )
        self._assert_started(version, allow_early=applied_pending)
        weight = q6(version.id_weight)
        return {"id_weight": weight, "debit": q6(Decimal(id_count) * weight)}

    # ── Reserve / commit / release ──────────────────────────────────────────

    def reserve(  # noqa: C901 - explicit FEFO/ledger flow is easier to audit
        self,
        organization_id: UUID,
        operation_key: str,
        id_count: int,
        actor_id: UUID | None = None,
    ) -> dict:
        existing = self.credit_repo.get_operation_by_key(
            organization_id, operation_key, for_update=True
        )
        if existing is not None:
            if existing.id_count != id_count:
                raise credit_error(
                    "OPERATION_KEY_CONFLICT",
                    "operation_key was already used with a different id_count",
                    status.HTTP_409_CONFLICT,
                )
            if existing.status in (
                GENERATION_STATUS_RESERVED,
                GENERATION_STATUS_COMMITTED,
            ):
                return self._operation_response(existing)
            raise credit_error(
                "OPERATION_KEY_CONFLICT",
                f"operation_key was already released ({existing.status})",
                status.HTTP_409_CONFLICT,
            )

        subscription, version, applied_pending = self._contract(organization_id)
        if subscription.status not in RESERVABLE_STATUSES:
            raise credit_error(
                "SUBSCRIPTION_INACTIVE",
                f"Subscription is {subscription.status}; issuance is paused",
                status.HTTP_402_PAYMENT_REQUIRED,
            )
        self._assert_started(version, allow_early=applied_pending)

        weight = q6(version.id_weight)
        debit = q6(Decimal(id_count) * weight)
        if debit <= 0:
            debit = SIX

        now = datetime.now(UTC)
        # FOR UPDATE cannot lock a row that does not exist yet. Claim the
        # operation key by inserting first; the unique constraint is the guard
        # and a concurrent duplicate is replayed instead of failing.
        try:
            operation = self.credit_repo.create_operation(
                {
                    "organization_id": organization_id,
                    "operation_key": operation_key,
                    "id_count": id_count,
                    "id_weight": weight,
                    "debit_qty": debit,
                    "status": GENERATION_STATUS_RESERVED,
                    "reserved_until": now + timedelta(minutes=RESERVATION_TTL_MINUTES),
                    "allocations": None,
                    "created_by": actor_id,
                }
            )
        except IntegrityError:
            self.db.rollback()
            existing = self.credit_repo.get_operation_by_key(
                organization_id, operation_key
            )
            if (
                existing is not None
                and existing.id_count == id_count
                and existing.status
                in (GENERATION_STATUS_RESERVED, GENERATION_STATUS_COMMITTED)
            ):
                return self._operation_response(existing)
            raise credit_error(
                "OPERATION_IN_PROGRESS",
                "The same operation_key is being processed concurrently",
                status.HTTP_409_CONFLICT,
            )

        batches = self.credit_repo.lock_eligible_batches(organization_id)
        total_available = sum((q6(batch.available_qty) for batch in batches), SIX * 0)
        if total_available < debit:
            self.db.rollback()
            raise credit_error(
                "INSUFFICIENT_CREDITS",
                "Not enough credits for this generation operation",
                status.HTTP_402_PAYMENT_REQUIRED,
                available=str(q6(total_available)),
                required=str(debit),
            )

        now = datetime.now(UTC)
        remaining = debit
        allocations = []
        running_balance = total_available
        for batch in batches:
            if remaining <= 0:
                break
            available = q6(batch.available_qty)
            take = min(available, remaining)
            if take <= 0:
                continue
            batch.reserved_qty = q6(batch.reserved_qty + take)
            running_balance = q6(running_balance - take)
            allocations.append(
                {
                    "batch_id": batch.id,
                    "quantity": take,
                    "expires_at": batch.expires_at,
                    "idempotency_key": f"reserve:{operation_key}:{batch.id}",
                    "balance_after": running_balance,
                }
            )
            remaining = q6(remaining - take)

        operation.allocations = [
            {
                "batch_id": str(a["batch_id"]),
                "quantity": str(a["quantity"]),
                "expires_at": a["expires_at"].isoformat(),
            }
            for a in allocations
        ]

        for allocation in allocations:
            self._write_ledger(
                organization_id=organization_id,
                batch_id=allocation["batch_id"],
                entry_type=LEDGER_RESERVE,
                qty=-allocation["quantity"],
                balance_after=allocation["balance_after"],
                operation_id=operation.id,
                idempotency_key=allocation["idempotency_key"],
                actor_id=actor_id,
                reason="Reservation for ID generation",
            )

        self.db.commit()
        return self._operation_response(operation)

    def commit(
        self, organization_id: UUID, operation_id: UUID, generated_count: int
    ) -> dict:
        operation = self.credit_repo.get_operation(
            organization_id, operation_id, for_update=True
        )
        if operation is None:
            raise credit_error(
                "OPERATION_NOT_FOUND",
                "Generation operation not found",
                status.HTTP_404_NOT_FOUND,
            )
        if operation.status == GENERATION_STATUS_COMMITTED:
            return self._operation_response(operation)
        if operation.status != GENERATION_STATUS_RESERVED:
            raise credit_error(
                "OPERATION_NOT_RESERVED",
                f"Operation is already {operation.status}",
                status.HTTP_409_CONFLICT,
            )
        now = datetime.now(UTC)
        if operation.reserved_until and _aware(operation.reserved_until) < now:
            raise credit_error(
                "RESERVATION_EXPIRED",
                "The reservation expired before commit; reserve again",
                status.HTTP_410_GONE,
            )
        if generated_count != operation.id_count:
            raise credit_error(
                "GENERATED_COUNT_MISMATCH",
                "Release the unused remainder before committing generated IDs",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                expected=operation.id_count,
                received=generated_count,
            )

        available = self.credit_repo.sum_available(organization_id, now)
        for allocation in self._allocations(operation):
            batch = self._locked_batch(organization_id, allocation["batch_id"])
            qty = q6(allocation["quantity"])
            batch.reserved_qty = q6(max(Decimal("0"), batch.reserved_qty - qty))
            batch.consumed_qty = q6(batch.consumed_qty + qty)
            if q6(batch.available_qty) <= 0:
                batch.status = CREDIT_BATCH_STATUS_EXHAUSTED
            # Availability is unchanged (reserved -> consumed); ``qty`` 0 is a
            # conversion marker. Balance reporting uses generation_operations.
            self._write_ledger(
                organization_id=organization_id,
                batch_id=batch.id,
                entry_type=LEDGER_CONSUME,
                qty=Decimal("0"),
                balance_after=available,
                operation_id=operation.id,
                idempotency_key=f"commit:{operation.id}:{batch.id}",
                reason="Reserved credits consumed",
            )

        operation.status = GENERATION_STATUS_COMMITTED
        operation.generated_count = generated_count
        self.db.commit()
        return self._operation_response(operation)

    def release(
        self, organization_id: UUID, operation_id: UUID, reason: str | None = None
    ) -> dict:
        operation = self.credit_repo.get_operation(
            organization_id, operation_id, for_update=True
        )
        if operation is None:
            raise credit_error(
                "OPERATION_NOT_FOUND",
                "Generation operation not found",
                status.HTTP_404_NOT_FOUND,
            )
        if operation.status == GENERATION_STATUS_RELEASED:
            return self._operation_response(operation)
        if operation.status == GENERATION_STATUS_COMMITTED:
            raise credit_error(
                "OPERATION_ALREADY_COMMITTED",
                "Committed credits cannot be released",
                status.HTTP_409_CONFLICT,
            )

        available = self.credit_repo.sum_available(organization_id)
        for allocation in self._allocations(operation):
            batch = self._locked_batch(organization_id, allocation["batch_id"])
            qty = q6(allocation["quantity"])
            batch.reserved_qty = q6(max(Decimal("0"), batch.reserved_qty - qty))
            available = q6(available + qty)
            self._write_ledger(
                organization_id=organization_id,
                batch_id=batch.id,
                entry_type=LEDGER_RELEASE,
                qty=qty,
                balance_after=available,
                operation_id=operation.id,
                idempotency_key=f"release:{operation.id}:{batch.id}",
                reason=reason or "Reservation released",
            )

        operation.status = GENERATION_STATUS_RELEASED
        self.db.commit()
        return self._operation_response(operation)

    # ── Grants, adjustments, expiry ─────────────────────────────────────────

    def grant_batch(
        self,
        *,
        organization_id: UUID,
        source_type: str,
        source_id: UUID | None,
        quantity: Decimal,
        expires_at: datetime | None = None,
        actor_id: UUID | None = None,
        idempotency_key: str | None = None,
        reason: str | None = None,
        commit: bool = True,
    ) -> dict:
        quantity = q6(quantity)
        if quantity <= 0:
            raise credit_error(
                "INVALID_QUANTITY",
                "Grant quantity must be positive",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        existing = self.credit_repo.get_batch_by_source(
            organization_id, source_type, source_id
        )
        if existing is not None:
            return self._batch_dict(existing)
        now = datetime.now(UTC)
        batch = self.credit_repo.create_batch(
            {
                "organization_id": organization_id,
                "source_type": source_type,
                "source_id": source_id,
                "granted_qty": quantity,
                "issued_at": now,
                "expires_at": expires_at or add_months(now, CREDIT_VALIDITY_MONTHS),
                "status": CREDIT_BATCH_STATUS_ACTIVE,
            }
        )
        balance_after = q6(self.credit_repo.sum_available(organization_id) + quantity)
        self._write_ledger(
            organization_id=organization_id,
            batch_id=batch.id,
            entry_type=LEDGER_GRANT,
            qty=quantity,
            balance_after=balance_after,
            reference_type=source_type,
            reference_id=source_id,
            idempotency_key=(
                idempotency_key or f"grant:{source_type}:{source_id or batch.id}"
            ),
            actor_id=actor_id,
            reason=reason or "Credit grant",
        )
        if commit:
            self.db.commit()
        return self._batch_dict(batch)

    def adjust(
        self,
        *,
        organization_id: UUID,
        direction: str,
        quantity: Decimal,
        reason: str,
        expires_at: datetime | None = None,
        actor_id: UUID | None = None,
        idempotency_key: str | None = None,
    ) -> dict:
        quantity = q6(quantity)
        ledger_key = (
            f"adjust:{idempotency_key}" if idempotency_key else f"adjust:{uuid4()}"
        )
        existing = self.credit_repo.get_ledger_by_idempotency(
            organization_id, ledger_key
        )
        if existing is not None:
            return {
                "organization_id": organization_id,
                "adjusted": str(abs(q6(existing.qty))),
                "replayed": True,
            }
        if direction == LEDGER_ADJUST_POSITIVE:
            source_id = uuid5(NAMESPACE_URL, f"adjust:{organization_id}:{ledger_key}")
            result = self.grant_batch(
                organization_id=organization_id,
                source_type="adjustment",
                source_id=source_id,
                quantity=quantity,
                expires_at=expires_at,
                actor_id=actor_id,
                idempotency_key=ledger_key,
            )
            result["replayed"] = False
            return result

        now = datetime.now(UTC)
        # Lock first, then check: two concurrent negative adjustments must
        # serialize on the batch rows, not race the aggregate check.
        batches = self.credit_repo.lock_eligible_batches(organization_id, now)
        available = sum((q6(batch.available_qty) for batch in batches), SIX * 0)
        if available < quantity:
            self.db.rollback()
            raise credit_error(
                "INSUFFICIENT_BALANCE",
                "Adjustment would take the credit balance below zero",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                available=str(available),
                required=str(quantity),
            )
        remaining = quantity
        running_balance = available
        for batch in batches:
            if remaining <= 0:
                break
            take = min(q6(batch.available_qty), remaining)
            if take <= 0:
                continue
            batch.reversed_qty = q6(batch.reversed_qty + take)
            running_balance = q6(running_balance - take)
            remaining = q6(remaining - take)
        if remaining > 0:
            self.db.rollback()
            raise credit_error(
                "INSUFFICIENT_BALANCE",
                "Adjustment could not be fully allocated",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                available=str(q6(available - quantity + remaining)),
                required=str(quantity),
            )
        self._write_ledger(
            organization_id=organization_id,
            batch_id=None,
            entry_type=LEDGER_ADJUST_NEGATIVE,
            qty=-quantity,
            balance_after=running_balance,
            idempotency_key=ledger_key,
            actor_id=actor_id,
            reason=reason,
        )
        self.db.commit()
        return {
            "organization_id": organization_id,
            "adjusted": str(quantity),
            "replayed": False,
        }

    def expire_due_batches(self, now: datetime | None = None) -> dict:
        now = now or datetime.now(UTC)
        expired = 0
        for batch in self.credit_repo.list_expired_candidates(now):
            quantity = q6(batch.available_qty)
            if quantity <= 0:
                continue
            batch.expired_qty = q6(batch.expired_qty + quantity)
            batch.status = CREDIT_BATCH_STATUS_EXPIRED
            balance_after = self.credit_repo.sum_available(batch.organization_id, now)
            self._write_ledger(
                organization_id=batch.organization_id,
                batch_id=batch.id,
                entry_type=LEDGER_EXPIRE,
                qty=-quantity,
                balance_after=balance_after,
                idempotency_key=f"expire:{batch.id}",
                reason="Batch expired",
            )
            expired += 1
        self.db.commit()
        return {"expired_batches": expired}

    # ── Account reads ───────────────────────────────────────────────────────

    def credits_summary(self, organization_id: UUID) -> dict:
        now = datetime.now(UTC)
        available = self.credit_repo.sum_available(organization_id, now)
        subscription = self.subscription_repo.get_subscription(organization_id)
        weight = Decimal("0")
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if subscription is not None:
            version = self.subscription_repo.get_version(subscription.plan_version_id)
            if version is not None:
                weight = q6(version.id_weight)
            if subscription.current_period_start:
                period_start = subscription.current_period_start
        earliest = self.credit_repo.earliest_expiring_batch(organization_id, now)
        estimated = int(available / weight) if weight > 0 else 0
        return {
            "available": available,
            "reserved": self.credit_repo.sum_reserved(organization_id),
            "used_this_period": self.credit_repo.used_since(
                organization_id, period_start
            ),
            "expiring_30_days": self.credit_repo.expiring_between(
                organization_id, now, now + timedelta(days=30)
            ),
            "expiring_60_days": self.credit_repo.expiring_between(
                organization_id, now, now + timedelta(days=60)
            ),
            "expiring_90_days": self.credit_repo.expiring_between(
                organization_id, now, now + timedelta(days=90)
            ),
            "earliest_expiry": (
                {
                    "batch_id": earliest.id,
                    "expires_at": earliest.expires_at,
                    "quantity": q6(earliest.available_qty),
                }
                if earliest
                else None
            ),
            "id_weight": weight,
            "estimated_ids_available": estimated,
            "as_of": now,
        }

    def expirations(self, organization_id: UUID) -> dict:
        now = datetime.now(UTC)
        horizon = now + timedelta(days=90)
        timeline = []
        for batch in self.credit_repo.list_expiring_batches(
            organization_id, now, horizon
        ):
            timeline.append(
                {
                    "batch_id": batch.id,
                    "expires_at": batch.expires_at,
                    "quantity": q6(batch.available_qty),
                    "source": batch.source_type,
                }
            )
        return {
            "buckets": {
                "within_30_days": self.credit_repo.expiring_between(
                    organization_id, now, now + timedelta(days=30)
                ),
                "within_60_days": self.credit_repo.expiring_between(
                    organization_id, now, now + timedelta(days=60)
                ),
                "within_90_days": self.credit_repo.expiring_between(
                    organization_id, now, horizon
                ),
            },
            "timeline": timeline,
        }

    def list_batches(
        self,
        organization_id: UUID,
        *,
        batch_status: str | None = None,
        expiring_before: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        items, total = self.credit_repo.list_batches(
            organization_id,
            status=batch_status,
            expiring_before=expiring_before,
            page=page,
            page_size=page_size,
        )
        invoice_ids = [
            batch.source_id
            for batch in items
            if batch.source_type == "invoice_plan" and batch.source_id
        ]
        invoice_numbers = {}
        if invoice_ids:
            for invoice_id, invoice_no in (
                self.db.query(Invoice.id, Invoice.invoice_no)
                .filter(Invoice.id.in_(invoice_ids))
                .all()
            ):
                invoice_numbers[invoice_id] = invoice_no
        return {
            "items": [
                {
                    "id": batch.id,
                    "source_type": batch.source_type,
                    "source_ref": invoice_numbers.get(batch.source_id),
                    "granted": q6(batch.granted_qty),
                    "remaining": q6(batch.available_qty),
                    "issued_at": batch.issued_at,
                    "expires_at": batch.expires_at,
                    "status": batch.status,
                }
                for batch in items
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": max(1, (total + page_size - 1) // page_size),
            },
        }

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
    ) -> dict:
        items, total = self.credit_repo.list_ledger(
            organization_id,
            entry_type=entry_type,
            from_date=from_date,
            to_date=to_date,
            operation_id=operation_id,
            page=page,
            page_size=page_size,
        )
        return {
            "transactions": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": max(1, (total + page_size - 1) // page_size),
            },
        }

    # ── Top-ups ─────────────────────────────────────────────────────────────

    def create_topup_quote(self, organization_id: UUID, credits: Decimal) -> tuple:
        subscription, version, applied_pending = self._contract(organization_id)
        if subscription.status not in RESERVABLE_STATUSES:
            raise credit_error(
                "TOPUP_NOT_ALLOWED",
                f"Top-ups are unavailable while the subscription is {subscription.status}",
                status.HTTP_409_CONFLICT,
            )
        if not version.topup_allowed:
            raise credit_error(
                "TOPUP_NOT_ALLOWED",
                "The current plan does not allow credit top-ups",
                status.HTTP_409_CONFLICT,
            )
        self._assert_started(version, allow_early=applied_pending)
        credits = q6(credits)
        unit_price = DEFAULT_TOPUP_UNIT_PRICE
        if version.included_credits and version.included_credits > 0:
            unit_price = Decimal(version.base_price) / Decimal(version.included_credits)
        subtotal = q2(credits * unit_price)
        tax_rate = Decimal(version.tax_rate or 0)
        tax = q2(subtotal * tax_rate / Decimal("100"))
        now = datetime.now(UTC)
        quote = self.credit_repo.create_quote(
            {
                "organization_id": organization_id,
                "plan_version_id": version.id,
                "credits": credits,
                "subtotal": subtotal,
                "tax_amount": tax,
                "amount": q2(subtotal + tax),
                "currency": self._currency(version.plan_id),
                "credit_expires_at": add_months(now, CREDIT_VALIDITY_MONTHS),
                "expires_at": now + timedelta(minutes=TOPUP_QUOTE_TTL_MINUTES),
            }
        )
        self.db.commit()
        return quote, subscription

    def create_topup_order(
        self,
        organization_id: UUID,
        quote_id: UUID,
        idempotency_key: str,
        provider: str | None = None,
        customer_email: str | None = None,
    ) -> dict:
        existing = self.credit_repo.get_order_by_idempotency(
            organization_id, idempotency_key
        )
        if existing is not None:
            return self._order_dict(existing)
        quote = self.credit_repo.get_quote(organization_id, quote_id, for_update=True)
        if quote is None:
            raise credit_error(
                "QUOTE_NOT_FOUND", "Top-up quote not found", status.HTTP_404_NOT_FOUND
            )
        now = datetime.now(UTC)
        if quote.consumed_at is not None or _aware(quote.expires_at) < now:
            raise credit_error(
                "INVALID_QUOTE",
                "This quote has expired or was already used",
                status.HTTP_400_BAD_REQUEST,
            )
        provider = (provider or "razorpay").lower()
        client = RazorpayService()
        if provider == "razorpay" and not client.enabled:
            raise credit_error(
                "PAYMENT_PROVIDER_NOT_CONFIGURED",
                "Razorpay checkout is not configured",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if (
            provider == "razorpay"
            and quote.currency.upper() != settings.razorpay_currency.upper()
        ):
            raise credit_error(
                "CURRENCY_NOT_SUPPORTED",
                f"Razorpay top-ups require {settings.razorpay_currency}",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        quote.consumed_at = now
        order = self.credit_repo.create_order(
            {
                "organization_id": organization_id,
                "quote_id": quote.id,
                "credits": quote.credits,
                "amount": quote.amount,
                "currency": quote.currency,
                "status": "created",
                "provider": provider,
                "idempotency_key": idempotency_key,
            }
        )
        self.db.flush()

        checkout = None
        if provider == "razorpay":
            amount_paise = int(
                (Decimal(order.amount) * 100).to_integral_value(rounding=ROUND_HALF_UP)
            )
            try:
                provider_order = client.create_order(
                    amount_paise=amount_paise,
                    receipt=f"topup-{order.id}",
                    notes={
                        "organization_id": str(organization_id),
                        "topup_order_id": str(order.id),
                        "credits": str(q6(order.credits)),
                    },
                )
            except HTTPException:
                order.status = "failed"
                self.db.commit()
                raise
            order.provider_ref = provider_order["id"]
            order.status = "pending"
            order.checkout_url = provider_order.get("short_url")
            checkout = {
                "provider": "razorpay",
                "key_id": client.key_id,
                "order_id": provider_order["id"],
                "amount": provider_order["amount"],
                "currency": provider_order["currency"],
                "name": settings.razorpay_company_name,
                "description": f"{q6(order.credits)} QR credits",
                "prefill": {"email": customer_email} if customer_email else {},
            }
        else:
            order.status = "pending"

        self.db.commit()
        return self._order_dict(order, checkout=checkout)

    def verify_topup_payment(
        self,
        organization_id: UUID,
        order_id: UUID,
        provider_order_id: str,
        provider_payment_id: str,
        signature: str,
    ) -> dict:
        """Verify the Checkout callback and grant credits (webhook fallback)."""
        order = self.credit_repo.get_order(organization_id, order_id, for_update=True)
        if order is None:
            raise credit_error(
                "ORDER_NOT_FOUND", "Top-up order not found", status.HTTP_404_NOT_FOUND
            )
        if order.status == "paid":
            return self._order_dict(order)
        if order.provider != "razorpay":
            raise credit_error(
                "PROVIDER_MISMATCH",
                "This order was not created with Razorpay",
                status.HTTP_409_CONFLICT,
            )
        if order.provider_ref and order.provider_ref != provider_order_id:
            raise credit_error(
                "ORDER_MISMATCH",
                "Razorpay order id does not match this top-up",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        client = RazorpayService()
        if not client.verify_checkout_signature(
            provider_order_id, provider_payment_id, signature
        ):
            raise credit_error(
                "SIGNATURE_INVALID",
                "Razorpay checkout signature is invalid",
                status.HTTP_400_BAD_REQUEST,
            )
        payment = client.fetch_payment(provider_payment_id)
        amount_paise = int(
            (Decimal(order.amount) * 100).to_integral_value(rounding=ROUND_HALF_UP)
        )
        if (
            payment.get("order_id") != provider_order_id
            or int(payment.get("amount", -1)) != amount_paise
            or payment.get("currency") != order.currency
        ):
            raise credit_error(
                "PAYMENT_MISMATCH",
                "Provider payment does not match the top-up order",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if payment.get("status") != "captured":
            raise credit_error(
                "PAYMENT_NOT_CAPTURED",
                f"Payment is {payment.get('status', 'unknown')}; wait for capture",
                status.HTTP_402_PAYMENT_REQUIRED,
            )
        if not order.provider_ref:
            order.provider_ref = provider_order_id
        return self.mark_topup_paid(organization_id, order.id, provider_payment_id)

    def mark_topup_paid(
        self,
        organization_id: UUID,
        order_id: UUID,
        provider_payment_id: str | None = None,
    ) -> dict:
        """Grant exactly one batch for a verified, captured payment."""
        order = self.credit_repo.get_order(organization_id, order_id, for_update=True)
        if order is None:
            raise credit_error(
                "ORDER_NOT_FOUND", "Top-up order not found", status.HTTP_404_NOT_FOUND
            )
        if order.status == "paid":
            return self._order_dict(order)
        quote = self.credit_repo.get_quote(organization_id, order.quote_id)
        order.status = "paid"
        order.paid_at = datetime.now(UTC)
        if provider_payment_id:
            order.provider_payment_id = provider_payment_id
        self.grant_batch(
            organization_id=organization_id,
            source_type="topup",
            source_id=order.id,
            quantity=order.credits,
            expires_at=quote.credit_expires_at if quote else None,
            commit=False,
        )
        self.db.commit()
        return self._order_dict(order)

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _currency(self, plan_id: UUID) -> str:
        plan = self.subscription_repo.get_plan(plan_id)
        return plan.currency if plan else "USD"

    def _locked_batch(self, organization_id: UUID, batch_id: UUID):
        from app.models.subscription import CreditBatch

        batch = (
            self.db.query(CreditBatch)
            .filter(
                CreditBatch.id == batch_id,
                CreditBatch.organization_id == organization_id,
            )
            .with_for_update()
            .first()
        )
        if batch is None:
            raise credit_error(
                "BATCH_NOT_FOUND", "Credit batch not found", status.HTTP_404_NOT_FOUND
            )
        return batch

    def _write_ledger(
        self,
        *,
        organization_id: UUID,
        batch_id: UUID | None,
        entry_type: str,
        qty: Decimal,
        balance_after: Decimal,
        idempotency_key: str,
        operation_id: UUID | None = None,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        actor_id: UUID | None = None,
        reason: str | None = None,
    ) -> None:
        if self.credit_repo.get_ledger_by_idempotency(organization_id, idempotency_key):
            return
        self.credit_repo.add_ledger(
            {
                "organization_id": organization_id,
                "batch_id": batch_id,
                "type": entry_type,
                "qty": q6(qty),
                "balance_after": q6(balance_after),
                "operation_id": operation_id,
                "reference_type": reference_type,
                "reference_id": reference_id,
                "idempotency_key": idempotency_key,
                "actor_id": actor_id,
                "reason": reason,
            }
        )

    @staticmethod
    def _allocations(operation) -> list[dict]:
        result = []
        for item in operation.allocations or []:
            result.append(
                {
                    "batch_id": UUID(str(item["batch_id"])),
                    "quantity": Decimal(str(item["quantity"])),
                }
            )
        return result

    def _operation_response(self, operation) -> dict:
        allocations = []
        for item in operation.allocations or []:
            allocations.append(
                {
                    "batch_id": UUID(str(item["batch_id"])),
                    "quantity": Decimal(str(item["quantity"])),
                    "expires_at": datetime.fromisoformat(str(item["expires_at"])),
                }
            )
        return {
            "operation_id": operation.id,
            "operation_key": operation.operation_key,
            "id_weight": q6(operation.id_weight),
            "debit": q6(operation.debit_qty),
            "reserved_until": operation.reserved_until,
            "allocations": allocations,
        }

    @staticmethod
    def _batch_dict(batch) -> dict:
        return {
            "id": batch.id,
            "source_type": batch.source_type,
            "source_ref": None,
            "granted": q6(batch.granted_qty),
            "remaining": q6(batch.available_qty),
            "issued_at": batch.issued_at,
            "expires_at": batch.expires_at,
            "status": batch.status,
        }

    @staticmethod
    def _order_dict(order, checkout: dict | None = None) -> dict:
        return {
            "order_id": order.id,
            "status": order.status,
            "checkout_url": order.checkout_url,
            "amount": order.amount,
            "currency": order.currency,
            "credits": q6(order.credits),
            "provider": order.provider,
            "provider_order_id": order.provider_ref,
            "provider_payment_id": order.provider_payment_id,
            "checkout": checkout,
        }
