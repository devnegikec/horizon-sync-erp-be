"""Charge Template repository for database operations"""

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.charge_template import ChargeTemplate


class ChargeTemplateRepository:
    """Repository for charge template database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, template_data: dict) -> ChargeTemplate:
        """
        Create a new charge template.

        Args:
            template_data: Dictionary containing template data

        Returns:
            Created ChargeTemplate object
        """
        template = ChargeTemplate(**template_data)
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def get_by_id(
        self, template_id: UUID, organization_id: UUID
    ) -> Optional[ChargeTemplate]:
        """
        Get charge template by ID within an organization.

        Args:
            template_id: Template UUID
            organization_id: Organization UUID

        Returns:
            ChargeTemplate object or None if not found
        """
        return (
            self.db.query(ChargeTemplate)
            .filter(
                ChargeTemplate.id == template_id,
                ChargeTemplate.organization_id == organization_id,
                ChargeTemplate.deleted_at.is_(None),
            )
            .first()
        )

    def get_by_code(
        self, template_code: str, organization_id: UUID
    ) -> Optional[ChargeTemplate]:
        """
        Get charge template by code within an organization.

        Args:
            template_code: Template code
            organization_id: Organization UUID

        Returns:
            ChargeTemplate object or None if not found
        """
        return (
            self.db.query(ChargeTemplate)
            .filter(
                ChargeTemplate.template_code == template_code,
                ChargeTemplate.organization_id == organization_id,
                ChargeTemplate.deleted_at.is_(None),
            )
            .first()
        )

    def update(self, template: ChargeTemplate, update_data: dict) -> ChargeTemplate:
        """
        Update charge template fields.

        Args:
            template: ChargeTemplate object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated ChargeTemplate object
        """
        for key, value in update_data.items():
            if hasattr(template, key) and value is not None:
                setattr(template, key, value)

        self.db.commit()
        self.db.refresh(template)
        return template

    def soft_delete(self, template: ChargeTemplate) -> ChargeTemplate:
        """
        Soft delete a charge template.

        Args:
            template: ChargeTemplate object to delete

        Returns:
            Deleted ChargeTemplate object
        """
        from datetime import UTC, datetime

        template.deleted_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(template)
        return template

    def list_templates(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        charge_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[ChargeTemplate], int]:
        """
        List charge templates with pagination and filters.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of templates per page
            charge_type: Filter by charge type
            is_active: Filter by active status
            search: Search term for template_code, template_name
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of templates, total count)
        """
        query = self.db.query(ChargeTemplate).filter(
            ChargeTemplate.organization_id == organization_id,
            ChargeTemplate.deleted_at.is_(None),
        )

        # Apply filters
        if charge_type:
            query = query.filter(ChargeTemplate.charge_type == charge_type)

        if is_active is not None:
            query = query.filter(ChargeTemplate.is_active == is_active)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (ChargeTemplate.template_code.ilike(search_term))
                | (ChargeTemplate.template_name.ilike(search_term))
            )

        # Get total count before pagination
        total_count = query.count()

        # Apply sorting
        sort_column = getattr(ChargeTemplate, sort_by, ChargeTemplate.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * page_size
        templates = query.offset(offset).limit(page_size).all()

        return templates, total_count

    def get_applicable_charges(
        self,
        organization_id: UUID,
        transaction_type: str,
        net_total: float,
        customer_location: Optional[dict] = None,
        total_weight: Optional[float] = None,
    ) -> list[ChargeTemplate]:
        """
        Get all applicable charge templates based on context.

        Args:
            organization_id: Organization UUID
            transaction_type: Transaction type
            net_total: Net total amount of transaction
            customer_location: Optional customer location dict
            total_weight: Optional total weight

        Returns:
            List of applicable ChargeTemplate objects
        """
        # Get all active charge templates for the organization
        templates = (
            self.db.query(ChargeTemplate)
            .filter(
                ChargeTemplate.organization_id == organization_id,
                ChargeTemplate.is_active == True,
                ChargeTemplate.deleted_at.is_(None),
            )
            .all()
        )

        # Filter by applicability rules
        applicable_templates = []
        for template in templates:
            if self._matches_applicability_rules(
                template, net_total, customer_location, total_weight
            ):
                applicable_templates.append(template)

        return applicable_templates

    def _matches_applicability_rules(
        self,
        template: ChargeTemplate,
        net_total: float,
        customer_location: Optional[dict] = None,
        total_weight: Optional[float] = None,
    ) -> bool:
        """
        Check if template's applicability rules match the given context.

        Args:
            template: ChargeTemplate to check
            net_total: Net total amount
            customer_location: Optional customer location dict
            total_weight: Optional total weight

        Returns:
            True if all rules match (AND logic), False otherwise
        """
        if not template.applicability_rules:
            return True

        rules = template.applicability_rules

        # Check min_order_value
        if "min_order_value" in rules:
            if net_total < rules["min_order_value"]:
                return False

        # Check max_order_value
        if "max_order_value" in rules:
            if net_total > rules["max_order_value"]:
                return False

        # Check customer_location
        if "customer_location" in rules and customer_location:
            rule_location = rules["customer_location"]
            if not self._matches_location(rule_location, customer_location):
                return False

        # Check min_weight
        if "min_weight" in rules and total_weight is not None:
            if total_weight < rules["min_weight"]:
                return False

        # Check max_weight
        if "max_weight" in rules and total_weight is not None:
            if total_weight > rules["max_weight"]:
                return False

        # Check shipping_zone
        if "shipping_zone" in rules and customer_location:
            # This would require zone mapping logic
            # For now, we'll skip this check
            pass

        return True

    def _matches_location(self, rule_location: dict, actual_location: dict) -> bool:
        """
        Check if actual location matches rule location.

        Args:
            rule_location: Location criteria from applicability rules
            actual_location: Actual location to check

        Returns:
            True if location matches, False otherwise
        """
        # Check country
        if "country" in rule_location:
            if actual_location.get("country") != rule_location["country"]:
                return False

        # Check state
        if "state" in rule_location:
            if actual_location.get("state") != rule_location["state"]:
                return False

        return True

    def template_code_exists(self, template_code: str, organization_id: UUID) -> bool:
        """
        Check if template code already exists in the organization.

        Args:
            template_code: Template code to check
            organization_id: Organization UUID

        Returns:
            True if template code exists, False otherwise
        """
        return (
            self.db.query(ChargeTemplate)
            .filter(
                ChargeTemplate.template_code == template_code,
                ChargeTemplate.organization_id == organization_id,
                ChargeTemplate.deleted_at.is_(None),
            )
            .count()
            > 0
        )

    def is_template_referenced(self, template_id: UUID, organization_id: UUID) -> dict:
        """
        Check if template is referenced by transactions.

        Args:
            template_id: Template UUID
            organization_id: Organization UUID

        Returns:
            Dictionary with lists of referencing entities
        """
        from app.models.transaction_breakdown import TransactionChargeBreakdown

        references = {"transactions": []}

        # Check transactions (charge breakdown)
        transactions = (
            self.db.query(TransactionChargeBreakdown.transaction_id)
            .filter(
                TransactionChargeBreakdown.organization_id == organization_id,
                TransactionChargeBreakdown.charge_template_id == template_id,
            )
            .distinct()
            .all()
        )
        references["transactions"] = [str(t[0]) for t in transactions]

        return references
