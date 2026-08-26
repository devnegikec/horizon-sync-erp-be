"""Maintain shortage balances against ASN lines and their latest receipt note."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.asn_order import AsnOrder
from app.models.inbound_short_balance import InboundShortBalance


class InboundShortBalanceService:
    """Projects approved-receipt quantities into a queryable short ledger."""

    def __init__(self, db: Session):
        self.db = db

    def refresh_for_asn(
        self,
        asn_order_id: UUID,
        organization_id: UUID,
        receiving_slip_id: UUID | None,
    ) -> None:
        asn = (
            self.db.query(AsnOrder)
            .filter(
                AsnOrder.id == asn_order_id,
                AsnOrder.organization_id == organization_id,
            )
            .first()
        )
        if asn is None:
            return

        for asn_item in asn.items:
            expected = Decimal(str(asn_item.qty or 0))
            received = Decimal(str(asn_item.delivered_qty or 0))
            short = max(Decimal("0"), expected - received)
            balance = (
                self.db.query(InboundShortBalance)
                .filter(
                    InboundShortBalance.organization_id == organization_id,
                    InboundShortBalance.asn_order_item_id == asn_item.id,
                )
                .first()
            )
            values = {
                "asn_order_id": asn.id,
                "receiving_slip_id": receiving_slip_id,
                "item_id": asn_item.item_id,
                "sku": (asn_item.item.sku or asn_item.item.item_code)
                if asn_item.item
                else str(asn_item.item_id),
                "expected_qty": expected,
                "received_qty": received,
                "short_qty": short,
                "status": "open" if short > 0 else "resolved",
            }
            if balance is None:
                self.db.add(
                    InboundShortBalance(
                        organization_id=organization_id,
                        asn_order_item_id=asn_item.id,
                        **values,
                    )
                )
            else:
                for name, value in values.items():
                    setattr(balance, name, value)
        self.db.commit()

    def list_for_asn(
        self, asn_order_id: UUID, organization_id: UUID
    ) -> list[InboundShortBalance]:
        return (
            self.db.query(InboundShortBalance)
            .filter(
                InboundShortBalance.asn_order_id == asn_order_id,
                InboundShortBalance.organization_id == organization_id,
            )
            .order_by(InboundShortBalance.sku)
            .all()
        )
