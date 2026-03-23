"""Service layer for Destinations module"""

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.currency_master import CurrencyMaster
from app.models.exchange_rate import ExchangeRate
from app.repositories.destination_market_repository import DestinationMarketRepository
from app.schemas.destination_market import DestinationMarketCreate, DestinationMarketUpdate


class DestinationMarketService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DestinationMarketRepository(db)

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

    def _enrich_currency(self, market, organization_id: UUID) -> dict | None:
        """Look up currency details from currency_masters."""
        if not market.currency_code:
            return None
        currency = (
            self.db.query(CurrencyMaster)
            .filter(
                CurrencyMaster.organization_id == organization_id,
                CurrencyMaster.code == market.currency_code,
                CurrencyMaster.deleted_at.is_(None),
            )
            .first()
        )
        if not currency:
            return None
        return {"code": currency.code, "name": currency.name, "symbol": currency.symbol}

    def _to_response(self, market, organization_id: UUID) -> dict:
        d = {c.name: getattr(market, c.name) for c in market.__table__.columns
             if c.name != "deleted_at"}
        d["currency"] = self._enrich_currency(market, organization_id)
        return d

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create(
        self, data: DestinationMarketCreate, organization_id: UUID, user_id: UUID
    ):
        if self.repo.code_exists(data.code, organization_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Market code '{data.code}' already exists for this organization.",
            )
        payload = data.model_dump()
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        market = self.repo.create(payload)
        return self._to_response(market, organization_id)

    def list_markets(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
        country: str | None = None,
        search: str | None = None,
    ):
        items, total = self.repo.list(organization_id, page, page_size, is_active, country, search)
        return {
            "markets": [self._to_response(m, organization_id) for m in items],
            "pagination": self._paginate(total, page, page_size),
        }

    def get_market(self, market_id: UUID, organization_id: UUID):
        market = self.repo.get_by_id(market_id, organization_id)
        if not market:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Destination market not found.")
        return self._to_response(market, organization_id)

    def update_market(
        self, market_id: UUID, data: DestinationMarketUpdate,
        organization_id: UUID, user_id: UUID
    ):
        market = self.repo.get_by_id(market_id, organization_id)
        if not market:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Destination market not found.")
        payload = {k: v for k, v in data.model_dump().items() if v is not None}
        payload["updated_by"] = user_id
        market = self.repo.update(market, payload)
        return self._to_response(market, organization_id)

    def delete_market(self, market_id: UUID, organization_id: UUID, user_id: UUID) -> None:
        market = self.repo.get_by_id(market_id, organization_id)
        if not market:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Destination market not found.")
        self.repo.soft_delete(market, user_id)

    # ── Currency by Destination ───────────────────────────────────────────────

    def get_currency_for_market(self, market_id: UUID, organization_id: UUID):
        """Return currency details + latest exchange rate to base currency."""
        market = self.repo.get_by_id(market_id, organization_id)
        if not market:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Destination market not found.")

        currency_info = self._enrich_currency(market, organization_id)
        currency_name = currency_info["name"] if currency_info else None
        currency_symbol = currency_info["symbol"] if currency_info else None

        # Try to find the latest exchange rate to base currency
        exchange_rate: Decimal | None = None
        if market.currency_code:
            # Find base currency for this org
            base = (
                self.db.query(CurrencyMaster)
                .filter(
                    CurrencyMaster.organization_id == organization_id,
                    CurrencyMaster.is_base_currency.is_(True),
                    CurrencyMaster.deleted_at.is_(None),
                )
                .first()
            )
            if base and base.code != market.currency_code:
                rate_row = (
                    self.db.query(ExchangeRate)
                    .filter(
                        ExchangeRate.from_currency == market.currency_code,
                        ExchangeRate.to_currency == base.code,
                    )
                    .order_by(ExchangeRate.effective_date.desc())
                    .first()
                )
                if rate_row:
                    exchange_rate = rate_row.rate

        return {
            "market_id": market.id,
            "market_code": market.code,
            "market_name": market.name,
            "currency_code": market.currency_code,
            "currency_name": currency_name,
            "currency_symbol": currency_symbol,
            "exchange_rate_to_base": exchange_rate,
        }
