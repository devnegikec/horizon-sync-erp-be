"""Razorpay webhook ingestion: signature verify, dedupe, reconcile, grant."""

import hashlib
import json
import logging
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.subscription import BillingProviderEvent
from app.repositories.credit_ledger_repository import CreditLedgerRepository
from app.services.credit_engine_service import CreditEngineService
from app.services.razorpay_service import RazorpayService

logger = logging.getLogger(__name__)

#: Events that settle a credit top-up.
PAID_EVENTS = {"payment.captured", "order.paid"}


class RazorpayWebhookService:
    def __init__(self, db: Session):
        self.db = db
        self.credit_repo = CreditLedgerRepository(db)
        self.credit = CreditEngineService(db)
        self.client = RazorpayService()

    def handle(self, raw_body: bytes, signature: str, event_id: str | None) -> dict:
        if not self.client.webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "WEBHOOK_NOT_CONFIGURED",
                    "message": "Razorpay webhook secret is not configured",
                },
            )
        if not self.client.verify_webhook_signature(raw_body, signature):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "SIGNATURE_INVALID",
                    "message": "Razorpay webhook signature is invalid",
                },
            )
        try:
            event = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_PAYLOAD",
                    "message": "Webhook body is not valid JSON",
                },
            ) from exc

        event_name = str(event.get("event") or "")
        event_key = event_id or hashlib.sha256(raw_body).hexdigest()

        record = (
            self.db.query(BillingProviderEvent)
            .filter(BillingProviderEvent.provider_event_id == event_key)
            .first()
        )
        if record is not None and record.processed_at is not None:
            return {"status": "duplicate", "event": event_name}
        if record is None:
            record = BillingProviderEvent(
                provider="razorpay",
                provider_event_id=event_key,
                event_type=event_name,
                payload=event,
                signature_verified=True,
            )
            self.db.add(record)
            try:
                self.db.flush()
            except IntegrityError:
                # Concurrent delivery of the same event id.
                self.db.rollback()
                record = (
                    self.db.query(BillingProviderEvent)
                    .filter(BillingProviderEvent.provider_event_id == event_key)
                    .first()
                )
                if record is not None and record.processed_at is not None:
                    return {"status": "duplicate", "event": event_name}
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "EVENT_IN_PROGRESS",
                        "message": "This webhook event is being processed",
                    },
                ) from None

        try:
            outcome = self._process_event(event, event_name)
            record.processed_at = datetime.now(UTC)
            self.db.commit()
            return outcome
        except Exception:
            # Roll back the event row too, so the provider's retry can process
            # it again instead of being treated as a duplicate.
            self.db.rollback()
            raise

    def _process_event(self, event: dict, event_name: str) -> dict:
        if event_name not in PAID_EVENTS:
            return {"status": "ignored", "event": event_name}

        payload = event.get("payload") or {}
        payment_entity = ((payload.get("payment") or {}).get("entity")) or {}
        order_entity = ((payload.get("order") or {}).get("entity")) or {}

        provider_order_id = payment_entity.get("order_id") or order_entity.get("id")
        provider_payment_id = payment_entity.get("id")
        if not provider_order_id or not provider_payment_id:
            logger.warning(
                "Razorpay %s missing order/payment id: keys=%s",
                event_name,
                list(payment_entity.keys()),
            )
            return {"status": "ignored", "event": event_name, "reason": "missing_ids"}

        order = self.credit_repo.get_order_by_provider_ref(
            "razorpay", str(provider_order_id), for_update=True
        )
        if order is None:
            logger.warning(
                "Razorpay %s for unknown order %s", event_name, provider_order_id
            )
            return {"status": "ignored", "event": event_name, "reason": "unknown_order"}

        if order.status == "paid":
            return {"status": "already_paid", "order_id": str(order.id)}

        expected_amount = int(
            (Decimal(order.amount) * 100).to_integral_value(rounding=ROUND_HALF_UP)
        )
        paid_amount = payment_entity.get("amount")
        if paid_amount is None:
            paid_amount = order_entity.get("amount")
        paid_currency = payment_entity.get("currency") or order_entity.get("currency")
        if int(paid_amount or -1) != expected_amount or (
            paid_currency and paid_currency != order.currency
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "PAYMENT_MISMATCH",
                    "message": "Webhook amount/currency does not match the order",
                },
            )

        # Never trust the webhook body alone: re-fetch the payment server-side.
        payment = self.client.fetch_payment(str(provider_payment_id))
        if (
            payment.get("order_id") != provider_order_id
            or int(payment.get("amount", -1)) != expected_amount
            or payment.get("currency") != order.currency
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "PAYMENT_MISMATCH",
                    "message": "Provider payment does not match the top-up order",
                },
            )
        if payment.get("status") != "captured":
            # Captured events will arrive later; keep the event unprocessed.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "PAYMENT_NOT_CAPTURED",
                    "message": f"Payment is {payment.get('status', 'unknown')}",
                },
            )

        self.credit.mark_topup_paid(
            order.organization_id, order.id, str(provider_payment_id)
        )
        return {"status": "paid", "order_id": str(order.id)}
