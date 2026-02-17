"""Account Balance model for tracking account balances over time"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.types import UUID as DBUUID


class AccountBalance(Base):
    """
    Account Balance model for tracking account balances over time.
    
    This model stores daily snapshots of account balances including:
    - Debit and credit totals
    - Net balance (calculated based on account type's natural balance)
    - Base currency equivalent for multi-currency accounts
    
    Balances are cached for performance and can be queried historically.
    """
    
    __tablename__ = "account_balances"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        DBUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    # Foreign key to account
    account_id: Mapped[UUID] = mapped_column(
        DBUUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Currency for this balance
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    
    # Balance components
    debit_total: Mapped[Decimal] = mapped_column(
        Numeric(19, 4),
        nullable=False,
        default=Decimal("0"),
        server_default="0"
    )
    
    credit_total: Mapped[Decimal] = mapped_column(
        Numeric(19, 4),
        nullable=False,
        default=Decimal("0"),
        server_default="0"
    )
    
    balance: Mapped[Decimal] = mapped_column(
        Numeric(19, 4),
        nullable=False,
        default=Decimal("0"),
        server_default="0"
    )
    
    base_currency_balance: Mapped[Decimal] = mapped_column(
        Numeric(19, 4),
        nullable=False,
        default=Decimal("0"),
        server_default="0"
    )
    
    # Date this balance is calculated as of
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    
    # Relationships
    account: Mapped["Account"] = relationship(
        "Account",
        back_populates="balances"
    )
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("account_id", "as_of_date", name="uq_account_balances_account_date"),
        Index("idx_account_balances_account_id", "account_id"),
        Index("idx_account_balances_as_of_date", "as_of_date"),
        Index("idx_account_balances_account_date", "account_id", "as_of_date"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<AccountBalance(id={self.id}, account_id={self.account_id}, "
            f"balance={self.balance}, as_of_date={self.as_of_date})>"
        )
