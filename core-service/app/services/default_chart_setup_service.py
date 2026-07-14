"""Default Chart Setup Service for creating default chart of accounts"""

import logging
import time
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.account_audit_log import AccountAuditLog, AuditAction
from app.repositories.chart_of_account_repository import AccountRepository
from app.schemas.chart_of_account import ChartOfAccountCreate
from app.schemas.chart_of_accounts_setup import DefaultChartResult
from app.services.chart_of_account_service import ChartOfAccountService
from app.services.default_account_service import DefaultAccountService
from app.services.default_account_template import (
    DEFAULT_MAPPINGS,
    get_default_account_structure,
)

logger = logging.getLogger(__name__)


class DefaultChartSetupService:
    """Service for creating default chart of accounts structure"""

    def __init__(self, db: Session):
        """
        Initialize the default chart setup service.

        Args:
            db: Database session
        """
        self.db = db
        self.account_repo = AccountRepository(db)
        self.chart_service = ChartOfAccountService(db)
        self.default_account_service = DefaultAccountService(db)

    def _validate_currency(self, currency: str) -> str:
        """
        Validate currency code and return valid code or default.

        Validates that the currency code is in the correct format (3 uppercase letters).
        If the currency is invalid or not specified, defaults to USD and logs a warning.

        Args:
            currency: ISO currency code to validate (e.g., "USD", "EUR")

        Returns:
            str: Validated currency code (uppercase) or "USD" if invalid

        Examples:
            >>> _validate_currency("usd")
            "USD"
            >>> _validate_currency("EURO")  # Invalid - 4 letters
            "USD"  # with warning logged
            >>> _validate_currency("")
            "USD"  # with warning logged
        """
        # Check if currency is empty or None
        if not currency:
            logger.warning(
                "Currency not specified, defaulting to USD",
                extra={
                    "provided_currency": currency,
                    "default_currency": "USD",
                    "event": "currency_validation_failed",
                },
            )
            return "USD"

        # Convert to uppercase for validation
        currency_upper = currency.upper()

        # Validate format: must be exactly 3 uppercase letters
        if len(currency_upper) != 3 or not currency_upper.isalpha():
            logger.warning(
                "Invalid currency code format, defaulting to USD",
                extra={
                    "provided_currency": currency,
                    "default_currency": "USD",
                    "validation_error": "Currency must be 3 letters",
                    "event": "currency_validation_failed",
                },
            )
            return "USD"

        # Currency is valid
        logger.debug(
            f"Currency validated: {currency_upper}",
            extra={
                "currency": currency_upper,
                "event": "currency_validated",
            },
        )

        return currency_upper

    def _log_account_creation(
        self,
        account,
        created_by: str,
        organization_id: UUID,
    ) -> None:
        """
        Log account creation to audit table.

        Creates an audit log entry for a newly created account with details
        about the account and marks it as created during default chart setup.

        Args:
            account: The created Account object
            created_by: User identifier who created the account
            organization_id: UUID of the organization

        Returns:
            None
        """
        audit_log = AccountAuditLog(
            account_id=account.id,
            action=AuditAction.CREATE.value,
            user_id=created_by,
            changes={
                "account_code": account.account_code,
                "account_name": account.account_name,
                "account_type": account.account_type.value,
                "currency": account.currency,
                "status": account.status.value,
                "source": "default_chart_setup",
            },
            audit_metadata={
                "organization_id": str(organization_id),
                "created_via": "default_chart_setup_service",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            timestamp=datetime.now(UTC),
        )
        self.db.add(audit_log)

        logger.debug(
            f"Created audit log for account {account.account_code}",
            extra={
                "account_id": str(account.id),
                "account_code": account.account_code,
                "organization_id": str(organization_id),
                "event": "account_audit_log_created",
            },
        )

    def create_default_chart_of_accounts(
        self,
        organization_id: UUID,
        currency: str,
        created_by: str,
    ) -> DefaultChartResult:
        """
        Create default chart of accounts with idempotency.

        This method creates a standard set of GL accounts and default account
        mappings for an organization. It is idempotent - calling it multiple
        times for the same organization will not create duplicate accounts.

        Steps:
        1. Check if default accounts already exist (idempotency)
        2. If exists, return existing accounts without creating duplicates
        3. Begin database transaction
        4. Create accounts using ChartOfAccountService.create() method
        5. Create accounts in dependency order (parents before children)
        6. Create default account mappings using DefaultAccountService
        7. Commit transaction
        8. Log creation event with structured logging
        9. Handle errors with rollback
        10. Return DefaultChartResult with accounts, mappings, already_existed flag

        Args:
            organization_id: UUID of the organization
            currency: ISO currency code (e.g., "USD")
            created_by: User identifier who created the organization

        Returns:
            DefaultChartResult with accounts, mappings, and already_existed flag

        Raises:
            Exception: If account creation fails (transaction will be rolled back)
        """
        # Step 1 & 2: Check if default accounts already exist (idempotency)
        if self.account_repo.check_default_accounts_exist(organization_id):
            logger.info(
                "Default accounts already exist for organization",
                extra={
                    "organization_id": str(organization_id),
                    "event": "chart_creation_skipped",
                },
            )

            # Get existing accounts and mappings
            templates = get_default_account_structure()
            account_codes = [t.account_code for t in templates]
            existing_accounts = self.account_repo.get_accounts_by_codes(
                organization_id, account_codes
            )

            # Get existing mappings
            existing_mappings = self.default_account_service.list_default_accounts(
                organization_id
            )

            # Convert to dict format for response
            accounts_list = [
                {
                    "id": str(acc.id),
                    "account_code": acc.account_code,
                    "account_name": acc.account_name,
                    "account_type": acc.account_type.value,
                }
                for acc in existing_accounts.values()
            ]

            mappings_list = [
                {
                    "id": str(m.id),
                    "transaction_type": m.transaction_type,
                    "scenario": m.scenario,
                    "account_id": str(m.account_id),
                }
                for m in existing_mappings
            ]

            return DefaultChartResult(
                accounts=accounts_list,
                mappings=mappings_list,
                already_existed=True,
            )

        # Step 3: Begin transaction (using existing session)
        # Validate and normalize currency
        validated_currency = self._validate_currency(currency)

        # Track start time for duration calculation
        start_time = time.time()
        start_timestamp = datetime.now(UTC).isoformat()

        logger.info(
            "Starting default chart creation",
            extra={
                "organization_id": str(organization_id),
                "currency": validated_currency,
                "created_by": created_by,
                "timestamp": start_timestamp,
                "event": "chart_creation_started",
            },
        )

        try:
            # Step 4 & 5: Create accounts in dependency order (parents before children)
            templates = get_default_account_structure()

            # Sort by level to ensure parents are created first
            templates_sorted = sorted(templates, key=lambda t: t.level)

            created_accounts = {}
            accounts_list = []

            for template in templates_sorted:
                # Determine parent_account_id if parent_code is specified
                parent_account_id = None
                if template.parent_code:
                    parent_account = created_accounts.get(template.parent_code)
                    if not parent_account:
                        logger.error(
                            f"Parent account {template.parent_code} not found for account {template.account_code}"
                        )
                        raise ValueError(
                            f"Parent account {template.parent_code} not found"
                        )
                    parent_account_id = parent_account.id

                # Create account using ChartOfAccountService
                account_data = ChartOfAccountCreate(
                    account_code=template.account_code,
                    account_name=template.account_name,
                    account_type=template.account_type.value,
                    parent_account_id=parent_account_id,
                    currency=validated_currency,
                    status="active",
                    is_posting_account=template.is_posting_account,
                    description=template.description,
                    opening_balance=None,  # No opening balance for default accounts
                )

                account = self.chart_service.create(
                    data=account_data,
                    organization_id=organization_id,
                    user_id=UUID(created_by) if created_by else organization_id,
                )

                # Create audit log entry for the created account
                self._log_account_creation(
                    account=account,
                    created_by=created_by,
                    organization_id=organization_id,
                )

                created_accounts[template.account_code] = account
                accounts_list.append(
                    {
                        "id": str(account.id),
                        "account_code": account.account_code,
                        "account_name": account.account_name,
                        "account_type": account.account_type.value,
                    }
                )

                logger.debug(
                    f"Created account {template.account_code} - {template.account_name}"
                )

            # Step 6: Create default account mappings
            mappings_list = []
            for mapping_key, mapping_config in DEFAULT_MAPPINGS.items():
                account_code = mapping_config["account_code"]
                account = created_accounts.get(account_code)

                if not account:
                    logger.warning(
                        f"Account {account_code} not found for mapping {mapping_key}, skipping"
                    )
                    continue

                try:
                    default_account = self.default_account_service.set_default_account(
                        transaction_type=mapping_config["transaction_type"],
                        account_id=account.id,
                        organization_id=organization_id,
                        scenario=mapping_config.get("scenario"),
                    )

                    mappings_list.append(
                        {
                            "id": str(default_account.id),
                            "transaction_type": default_account.transaction_type,
                            "scenario": default_account.scenario,
                            "account_id": str(default_account.account_id),
                        }
                    )

                    logger.debug(
                        f"Created default mapping: {mapping_config['transaction_type']} -> {account_code}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to create default mapping {mapping_key}: {e}"
                    )
                    # Continue with other mappings even if one fails

            # Step 7: Commit transaction
            self.db.commit()

            # Calculate duration
            duration_seconds = time.time() - start_time
            completion_timestamp = datetime.now(UTC).isoformat()

            # Step 8: Log creation event
            logger.info(
                "Default chart creation completed",
                extra={
                    "organization_id": str(organization_id),
                    "currency": validated_currency,
                    "created_by": created_by,
                    "accounts_created": len(accounts_list),
                    "mappings_created": len(mappings_list),
                    "duration_seconds": round(duration_seconds, 3),
                    "timestamp": completion_timestamp,
                    "event": "chart_creation_completed",
                },
            )

            # Step 10: Return result
            return DefaultChartResult(
                accounts=accounts_list,
                mappings=mappings_list,
                already_existed=False,
            )

        except Exception as e:
            # Step 9: Handle errors with rollback
            self.db.rollback()
            
            error_timestamp = datetime.now(UTC).isoformat()
            
            logger.error(
                "Default chart creation failed",
                extra={
                    "organization_id": str(organization_id),
                    "currency": validated_currency,
                    "created_by": created_by,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "timestamp": error_timestamp,
                    "event": "chart_creation_failed",
                },
            )
            raise
