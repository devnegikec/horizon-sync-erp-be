"""Charge Template service for business logic"""

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.charge_template import ChargeTemplate
from app.repositories.charge_template_repository import ChargeTemplateRepository


class ChargeTemplateService:
    """Service for charge template business logic"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ChargeTemplateRepository(db)

    def create_template(self, template_data: dict, user_id: UUID) -> dict:
        """
        Create a new charge template.

        Args:
            template_data: Dictionary containing template data
            user_id: User ID for audit trail

        Returns:
            Created charge template as dict

        Raises:
            ValueError: If validation fails
        """
        # Validate required fields
        self._validate_required_fields(template_data)

        # Check for duplicate template_code
        if self.repo.template_code_exists(
            template_data["template_code"], template_data["organization_id"]
        ):
            raise ValueError(
                f"Template code '{template_data['template_code']}' already exists"
            )

        # Prepare payload
        payload = dict(template_data)
        payload["created_by"] = user_id
        payload["updated_by"] = user_id

        # Create template
        template = self.repo.create(payload)
        return self._to_response(template)

    def get_template(self, template_id: UUID, organization_id: UUID) -> dict:
        """
        Get charge template by ID.

        Args:
            template_id: Template UUID
            organization_id: Organization UUID

        Returns:
            Charge template as dict

        Raises:
            ResourceNotFoundException: If template not found
        """
        template = self.repo.get_by_id(template_id, organization_id)
        if not template:
            raise ResourceNotFoundException(f"Charge template {template_id} not found")
        return self._to_response(template)

    def update_template(
        self, template_id: UUID, template_data: dict, user_id: UUID
    ) -> dict:
        """
        Update charge template.

        Args:
            template_id: Template UUID
            template_data: Dictionary containing fields to update
            user_id: User ID for audit trail

        Returns:
            Updated charge template as dict

        Raises:
            ResourceNotFoundException: If template not found
            ValueError: If validation fails
        """
        organization_id = template_data.get("organization_id")
        if not organization_id:
            raise ValueError("organization_id is required")

        template = self.repo.get_by_id(template_id, organization_id)
        if not template:
            raise ResourceNotFoundException(f"Charge template {template_id} not found")

        # Check for duplicate template_code if being updated
        if "template_code" in template_data:
            new_code = template_data["template_code"]
            if new_code != template.template_code:
                if self.repo.template_code_exists(new_code, organization_id):
                    raise ValueError(f"Template code '{new_code}' already exists")

        # Validate calculation method fields if being updated
        if "calculation_method" in template_data or any(
            k in template_data for k in ["fixed_amount", "percentage_rate", "base_on"]
        ):
            self._validate_calculation_fields(
                {
                    "calculation_method": template_data.get(
                        "calculation_method", template.calculation_method
                    ),
                    "fixed_amount": template_data.get(
                        "fixed_amount", template.fixed_amount
                    ),
                    "percentage_rate": template_data.get(
                        "percentage_rate", template.percentage_rate
                    ),
                    "base_on": template_data.get("base_on", template.base_on),
                }
            )

        # Prepare update payload
        payload = {k: v for k, v in template_data.items() if k != "organization_id"}
        payload["updated_by"] = user_id

        # Update template
        updated_template = self.repo.update(template, payload)
        return self._to_response(updated_template)

    def delete_template(self, template_id: UUID, organization_id: UUID) -> None:
        """
        Soft delete charge template with reference checking.

        Args:
            template_id: Template UUID
            organization_id: Organization UUID

        Raises:
            ResourceNotFoundException: If template not found
            ValueError: If template is referenced by transactions
        """
        template = self.repo.get_by_id(template_id, organization_id)
        if not template:
            raise ResourceNotFoundException(f"Charge template {template_id} not found")

        # Check for references
        references = self.repo.is_template_referenced(template_id, organization_id)
        if references["transactions"]:
            raise ValueError(
                f"Cannot delete charge template that is referenced by "
                f"{len(references['transactions'])} transactions"
            )

        # Soft delete
        self.repo.soft_delete(template)

    def list_templates(
        self, organization_id: UUID, filters: dict | None = None
    ) -> tuple[list[dict], dict]:
        """
        List charge templates with pagination and filters.

        Args:
            organization_id: Organization UUID
            filters: Optional dictionary containing filter parameters

        Returns:
            Tuple of (list of templates, pagination info)
        """
        filters = filters or {}

        templates, total = self.repo.list_templates(
            organization_id=organization_id,
            page=filters.get("page", 1),
            page_size=filters.get("page_size", 20),
            charge_type=filters.get("charge_type"),
            is_active=filters.get("is_active"),
            search=filters.get("search"),
            sort_by=filters.get("sort_by", "created_at"),
            sort_order=filters.get("sort_order", "desc"),
        )

        page = filters.get("page", 1)
        page_size = filters.get("page_size", 20)
        total_pages = (total + page_size - 1) // page_size if page_size else 0

        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

        return [self._to_list_item(t) for t in templates], pagination

    def get_applicable_charges(self, context: dict) -> list[dict]:
        """
        Get all applicable charge templates based on context.

        Args:
            context: Dictionary containing:
                - organization_id: UUID
                - transaction_type: str
                - net_total: float
                - customer_location: Optional[dict]
                - total_weight: Optional[float]

        Returns:
            List of applicable charge templates as dicts
        """
        templates = self.repo.get_applicable_charges(
            organization_id=context["organization_id"],
            transaction_type=context["transaction_type"],
            net_total=context["net_total"],
            customer_location=context.get("customer_location"),
            total_weight=context.get("total_weight"),
        )

        return [self._to_response(template) for template in templates]

    def _validate_required_fields(self, template_data: dict) -> None:
        """
        Validate required fields for charge template creation.

        Args:
            template_data: Template data to validate

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = [
            "template_name",
            "charge_type",
            "organization_id",
            "calculation_method",
        ]
        missing_fields = [f for f in required_fields if f not in template_data]

        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Validate charge_type if provided
        if "charge_type" in template_data:
            valid_types = ["Shipping", "Handling", "Packaging", "Insurance", "Custom"]
            if template_data["charge_type"] not in valid_types:
                raise ValueError(
                    f"Invalid charge_type. Must be one of: {', '.join(valid_types)}"
                )

        # Validate calculation method fields
        self._validate_calculation_fields(template_data)

    def _validate_calculation_fields(self, template_data: dict) -> None:
        """
        Validate calculation method specific fields.

        Args:
            template_data: Template data to validate

        Raises:
            ValueError: If calculation method fields are invalid
        """
        calculation_method = template_data.get("calculation_method")

        if calculation_method == "FIXED":
            if template_data.get("fixed_amount") is None:
                raise ValueError(
                    "fixed_amount is required when calculation_method is FIXED"
                )
            if template_data.get("fixed_amount", 0) < 0:
                raise ValueError("fixed_amount cannot be negative")

        elif calculation_method == "PERCENTAGE":
            if template_data.get("percentage_rate") is None:
                raise ValueError(
                    "percentage_rate is required when calculation_method is PERCENTAGE"
                )
            if template_data.get("base_on") is None:
                raise ValueError(
                    "base_on is required when calculation_method is PERCENTAGE"
                )

            if template_data.get("percentage_rate", 0) < 0:
                raise ValueError("percentage_rate cannot be negative")

            valid_base_on = ["Net_Total", "Grand_Total"]
            if template_data.get("base_on") not in valid_base_on:
                raise ValueError(
                    f"Invalid base_on. Must be one of: {', '.join(valid_base_on)}"
                )

        elif calculation_method:
            raise ValueError("Invalid calculation_method. Must be FIXED or PERCENTAGE")

    @staticmethod
    def _to_response(template: ChargeTemplate) -> dict:
        """Convert ChargeTemplate model to response dict"""
        return {
            "id": template.id,
            "organization_id": template.organization_id,
            "template_code": template.template_code,
            "template_name": template.template_name,
            "charge_type": template.charge_type,
            "description": template.description,
            "calculation_method": template.calculation_method,
            "fixed_amount": template.fixed_amount,
            "percentage_rate": template.percentage_rate,
            "base_on": template.base_on,
            "account_head_id": template.account_head_id,
            "is_active": template.is_active,
            "applicability_rules": template.applicability_rules,
            "extra_data": template.extra_data,
            "created_by": template.created_by,
            "updated_by": template.updated_by,
            "created_at": template.created_at,
            "updated_at": template.updated_at,
        }

    @staticmethod
    def _to_list_item(template: ChargeTemplate) -> dict:
        """Convert ChargeTemplate model to list item dict"""
        return {
            "id": template.id,
            "organization_id": template.organization_id,
            "template_code": template.template_code,
            "template_name": template.template_name,
            "charge_type": template.charge_type,
            "calculation_method": template.calculation_method,
            "is_active": template.is_active,
            "created_at": template.created_at,
            "updated_at": template.updated_at,
        }
