"""Tax Template service for business logic"""

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.events.publisher import get_event_publisher
from app.models.tax_template import TaxTemplate
from app.repositories.tax_template_repository import TaxTemplateRepository

logger = logging.getLogger(__name__)


@dataclass
class TaxContext:
    """Context for determining applicable tax template"""

    organization_id: UUID
    transaction_type: str  # "Sales" or "Purchase"
    item_id: UUID | None = None
    item_group_id: UUID | None = None
    customer_id: UUID | None = None
    supplier_id: UUID | None = None
    shipping_address: dict | None = None


class TaxTemplateService:
    """Service for tax template business logic"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = TaxTemplateRepository(db)

    def create_template(self, template_data: dict, user_id: UUID) -> dict:
        """
        Create a new tax template with tax rules.

        Args:
            template_data: Dictionary containing template data including tax_rules
            user_id: User ID for audit trail

        Returns:
            Created tax template as dict

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

        # Handle default template logic
        if payload.get("is_default", False):
            self.repo.unmark_default_templates(
                payload["organization_id"], payload["tax_category"]
            )

        # Create template
        template = self.repo.create(payload)

        # Publish entity created event
        try:
            event_publisher = get_event_publisher()
            # Convert SQLAlchemy model to dict
            template_data = {
                k: v for k, v in template.__dict__.items() if not k.startswith("_")
            }
            event_publisher.publish_entity_created(
                entity_type="tax_templates",
                entity_id=str(template.id),
                organization_id=str(template_data["organization_id"]),
                data=template_data,
            )
        except Exception as e:
            logger.error(f"Failed to publish tax template created event: {e}")

        return self._to_response(template)

    def get_template(self, template_id: UUID, organization_id: UUID) -> dict:
        """
        Get tax template by ID.

        Args:
            template_id: Template UUID
            organization_id: Organization UUID

        Returns:
            Tax template as dict

        Raises:
            ResourceNotFoundException: If template not found
        """
        template = self.repo.get_by_id(template_id, organization_id)
        if not template:
            raise ResourceNotFoundException(f"Tax template {template_id} not found")
        return self._to_response(template)

    def update_template(
        self, template_id: UUID, template_data: dict, user_id: UUID
    ) -> dict:
        """
        Update tax template.

        Args:
            template_id: Template UUID
            template_data: Dictionary containing fields to update
            user_id: User ID for audit trail

        Returns:
            Updated tax template as dict

        Raises:
            ResourceNotFoundException: If template not found
            ValueError: If validation fails
        """
        organization_id = template_data.get("organization_id")
        if not organization_id:
            raise ValueError("organization_id is required")

        template = self.repo.get_by_id(template_id, organization_id)
        if not template:
            raise ResourceNotFoundException(f"Tax template {template_id} not found")

        # Check for duplicate template_code if being updated
        if "template_code" in template_data:
            new_code = template_data["template_code"]
            if new_code != template.template_code:
                if self.repo.template_code_exists(new_code, organization_id):
                    raise ValueError(f"Template code '{new_code}' already exists")

        # Prepare update payload
        payload = {k: v for k, v in template_data.items() if k != "organization_id"}
        payload["updated_by"] = user_id

        # Handle default template logic
        if payload.get("is_default", False) and not template.is_default:
            self.repo.unmark_default_templates(organization_id, template.tax_category)

        # Update template
        updated_template = self.repo.update(template, payload)

        # Publish entity updated event
        try:
            event_publisher = get_event_publisher()
            # Convert SQLAlchemy model to dict
            template_data = {
                k: v
                for k, v in updated_template.__dict__.items()
                if not k.startswith("_")
            }
            event_publisher.publish_entity_updated(
                entity_type="tax_templates",
                entity_id=str(template_id),
                organization_id=str(organization_id),
                data=template_data,
            )
        except Exception as e:
            logger.error(f"Failed to publish tax template updated event: {e}")

        return self._to_response(updated_template)

    def delete_template(self, template_id: UUID, organization_id: UUID) -> None:
        """
        Soft delete tax template with reference checking.

        Args:
            template_id: Template UUID
            organization_id: Organization UUID

        Raises:
            ResourceNotFoundException: If template not found
            ValueError: If template is referenced by items, item_groups, or transactions
        """
        template = self.repo.get_by_id(template_id, organization_id)
        if not template:
            raise ResourceNotFoundException(f"Tax template {template_id} not found")

        # Check for references
        references = self.repo.is_template_referenced(template_id, organization_id)
        if any(references.values()):
            raise ValueError(
                f"Cannot delete tax template that is referenced by "
                f"{len(references['items'])} items, "
                f"{len(references['item_groups'])} item groups, "
                f"and {len(references['transactions'])} transactions"
            )

        # Soft delete
        self.repo.soft_delete(template)

        # Publish entity deleted event
        try:
            event_publisher = get_event_publisher()
            event_publisher.publish_entity_deleted(
                entity_type="tax_templates",
                entity_id=str(template_id),
                organization_id=str(organization_id),
            )
        except Exception as e:
            logger.error(f"Failed to publish tax template deleted event: {e}")

    def list_templates(
        self, organization_id: UUID, filters: dict | None = None
    ) -> tuple[list[dict], dict]:
        """
        List tax templates with pagination and filters.

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
            tax_category=filters.get("tax_category"),
            is_active=filters.get("is_active"),
            is_default=filters.get("is_default"),
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

    def set_as_default(
        self, template_id: UUID, organization_id: UUID, tax_category: str
    ) -> dict:
        """
        Set a tax template as default for an organization and tax category.

        Args:
            template_id: Template UUID
            organization_id: Organization UUID
            tax_category: Tax category (Input or Output)

        Returns:
            Updated tax template as dict

        Raises:
            ResourceNotFoundException: If template not found
            ValueError: If tax_category doesn't match template
        """
        template = self.repo.get_by_id(template_id, organization_id)
        if not template:
            raise ResourceNotFoundException(f"Tax template {template_id} not found")

        if template.tax_category != tax_category:
            raise ValueError(
                f"Template tax_category '{template.tax_category}' "
                f"does not match requested category '{tax_category}'"
            )

        # Unmark existing default templates
        self.repo.unmark_default_templates(organization_id, tax_category)

        # Set this template as default
        payload = {"is_default": True, "updated_by": template.updated_by}
        updated_template = self.repo.update(template, payload)
        return self._to_response(updated_template)

    def get_applicable_template(self, context: TaxContext) -> tuple | None:
        """
        Get applicable tax template based on context using inheritance hierarchy.

        Args:
            context: TaxContext object containing transaction details

        Returns:
            Tuple of (template dict, source string), or None if no applicable template
        """
        result = self.repo.get_applicable_template(
            organization_id=context.organization_id,
            transaction_type=context.transaction_type,
            item_id=context.item_id,
            item_group_id=context.item_group_id,
            customer_location=context.shipping_address,
            supplier_location=None,
        )

        if result:
            template, source = result
            return (self._to_response(template), source)

        return None

    def _validate_required_fields(self, template_data: dict) -> None:
        """
        Validate required fields for tax template creation.

        Args:
            template_data: Template data to validate

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ["template_name", "organization_id", "is_active"]
        missing_fields = [f for f in required_fields if f not in template_data]

        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Validate tax_category if provided
        if "tax_category" in template_data:
            valid_categories = ["Input", "Output"]
            if template_data["tax_category"] not in valid_categories:
                raise ValueError(
                    f"Invalid tax_category. Must be one of: {', '.join(valid_categories)}"
                )

    @staticmethod
    def _to_response(template: TaxTemplate) -> dict:
        """Convert TaxTemplate model to response dict"""
        return {
            "id": template.id,
            "organization_id": template.organization_id,
            "template_code": template.template_code,
            "template_name": template.template_name,
            "description": template.description,
            "tax_category": template.tax_category,
            "is_default": template.is_default,
            "is_active": template.is_active,
            "applicability_rules": template.applicability_rules,
            "extra_data": template.extra_data,
            "created_by": template.created_by,
            "updated_by": template.updated_by,
            "created_at": template.created_at,
            "updated_at": template.updated_at,
            "tax_rules": [
                {
                    "id": rule.id,
                    "tax_template_id": rule.tax_template_id,
                    "rule_name": rule.rule_name,
                    "tax_type": rule.tax_type,
                    "description": rule.description,
                    "tax_rate": rule.tax_rate,
                    "account_head_id": rule.account_head_id,
                    "is_compound": rule.is_compound,
                    "sequence": rule.sequence,
                    "applicability_conditions": rule.applicability_conditions,
                    "created_at": rule.created_at,
                    "updated_at": rule.updated_at,
                }
                for rule in template.tax_rules
            ],
        }

    @staticmethod
    def _to_list_item(template: TaxTemplate) -> dict:
        """Convert TaxTemplate model to list item dict"""
        return {
            "id": template.id,
            "organization_id": template.organization_id,
            "template_code": template.template_code,
            "template_name": template.template_name,
            "tax_category": template.tax_category,
            "is_default": template.is_default,
            "is_active": template.is_active,
            "tax_rules_count": len(template.tax_rules),
            "created_at": template.created_at,
            "updated_at": template.updated_at,
        }
