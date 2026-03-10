"""Tax Template repository for database operations"""

from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.tax_template import TaxRule, TaxTemplate


class TaxTemplateRepository:
    """Repository for tax template database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, template_data: dict) -> TaxTemplate:
        """
        Create a new tax template with tax rules.

        Args:
            template_data: Dictionary containing template data including tax_rules

        Returns:
            Created TaxTemplate object
        """
        # Extract tax_rules if present
        tax_rules_data = template_data.pop("tax_rules", [])

        # Create template
        template = TaxTemplate(**template_data)

        # Create tax rules
        for rule_data in tax_rules_data:
            tax_rule = TaxRule(**rule_data)
            template.tax_rules.append(tax_rule)

        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def get_by_id(
        self, template_id: UUID, organization_id: UUID, include_rules: bool = True
    ) -> TaxTemplate | None:
        """
        Get tax template by ID within an organization.

        Args:
            template_id: Template UUID
            organization_id: Organization UUID
            include_rules: Whether to include tax_rules relationship

        Returns:
            TaxTemplate object or None if not found
        """
        query = self.db.query(TaxTemplate).filter(
            TaxTemplate.id == template_id,
            TaxTemplate.organization_id == organization_id,
            TaxTemplate.deleted_at.is_(None),
        )

        if include_rules:
            query = query.options(joinedload(TaxTemplate.tax_rules))

        return query.first()

    def get_by_code(
        self, template_code: str, organization_id: UUID
    ) -> TaxTemplate | None:
        """
        Get tax template by code within an organization.

        Args:
            template_code: Template code
            organization_id: Organization UUID

        Returns:
            TaxTemplate object or None if not found
        """
        return (
            self.db.query(TaxTemplate)
            .filter(
                TaxTemplate.template_code == template_code,
                TaxTemplate.organization_id == organization_id,
                TaxTemplate.deleted_at.is_(None),
            )
            .first()
        )

    def update(self, template: TaxTemplate, update_data: dict) -> TaxTemplate:
        """
        Update tax template fields.

        Args:
            template: TaxTemplate object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated TaxTemplate object
        """
        # Handle tax_rules separately if present
        tax_rules_data = update_data.pop("tax_rules", None)

        # Update template fields
        for key, value in update_data.items():
            if hasattr(template, key) and value is not None:
                setattr(template, key, value)

        # Update tax rules if provided
        if tax_rules_data is not None:
            # Remove existing rules
            for rule in template.tax_rules:
                self.db.delete(rule)

            # Add new rules
            for rule_data in tax_rules_data:
                tax_rule = TaxRule(**rule_data, tax_template_id=template.id)
                template.tax_rules.append(tax_rule)

        self.db.commit()
        self.db.refresh(template)
        return template

    def soft_delete(self, template: TaxTemplate) -> TaxTemplate:
        """
        Soft delete a tax template.

        Args:
            template: TaxTemplate object to delete

        Returns:
            Deleted TaxTemplate object
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
        tax_category: str | None = None,
        is_active: bool | None = None,
        is_default: bool | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[TaxTemplate], int]:
        """
        List tax templates with pagination and filters.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of templates per page
            tax_category: Filter by tax category (Input/Output)
            is_active: Filter by active status
            is_default: Filter by default status
            search: Search term for template_code, template_name
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of templates, total count)
        """
        query = (
            self.db.query(TaxTemplate)
            .filter(
                TaxTemplate.organization_id == organization_id,
                TaxTemplate.deleted_at.is_(None),
            )
            .options(joinedload(TaxTemplate.tax_rules))
        )

        # Apply filters
        if tax_category:
            query = query.filter(TaxTemplate.tax_category == tax_category)

        if is_active is not None:
            query = query.filter(TaxTemplate.is_active == is_active)

        if is_default is not None:
            query = query.filter(TaxTemplate.is_default == is_default)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (TaxTemplate.template_code.ilike(search_term))
                | (TaxTemplate.template_name.ilike(search_term))
            )

        # Get total count before pagination
        total_count = query.count()

        # Apply sorting
        sort_column = getattr(TaxTemplate, sort_by, TaxTemplate.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * page_size
        templates = query.offset(offset).limit(page_size).all()

        return templates, total_count

    def get_default_template(
        self, organization_id: UUID, tax_category: str
    ) -> TaxTemplate | None:
        """
        Get the default tax template for an organization and tax category.

        Args:
            organization_id: Organization UUID
            tax_category: Tax category (Input or Output)

        Returns:
            Default TaxTemplate object or None if not found
        """
        return (
            self.db.query(TaxTemplate)
            .filter(
                TaxTemplate.organization_id == organization_id,
                TaxTemplate.tax_category == tax_category,
                TaxTemplate.is_default == True,
                TaxTemplate.is_active == True,
                TaxTemplate.deleted_at.is_(None),
            )
            .options(joinedload(TaxTemplate.tax_rules))
            .first()
        )

    def unmark_default_templates(
        self, organization_id: UUID, tax_category: str
    ) -> None:
        """
        Unmark all default templates for an organization and tax category.

        Args:
            organization_id: Organization UUID
            tax_category: Tax category (Input or Output)
        """
        self.db.query(TaxTemplate).filter(
            TaxTemplate.organization_id == organization_id,
            TaxTemplate.tax_category == tax_category,
            TaxTemplate.is_default == True,
            TaxTemplate.deleted_at.is_(None),
        ).update({"is_default": False})
        self.db.commit()

    def get_applicable_template(
        self,
        organization_id: UUID,
        transaction_type: str,
        item_id: UUID | None = None,
        item_group_id: UUID | None = None,
        customer_location: dict | None = None,
        supplier_location: dict | None = None,
    ) -> tuple[TaxTemplate, str] | None:
        """
        Get the applicable tax template based on context and inheritance hierarchy.

        Hierarchy: item > item_group > organization default

        Args:
            organization_id: Organization UUID
            transaction_type: Transaction type (Sales or Purchase)
            item_id: Optional item UUID
            item_group_id: Optional item group UUID
            customer_location: Optional customer location dict
            supplier_location: Optional supplier location dict

        Returns:
            Tuple of (TaxTemplate, source) where source is "item", "item_group", or "organization_default"
            Returns None if no applicable template found
        """
        # Determine tax category based on transaction type
        tax_category = "Output" if transaction_type == "Sales" else "Input"
        template_field = (
            "sales_tax_template_id"
            if transaction_type == "Sales"
            else "purchase_tax_template_id"
        )

        # 1. Check item-level template
        if item_id:
            from app.models.item import Item

            item = (
                self.db.query(Item)
                .filter(
                    Item.id == item_id,
                    Item.organization_id == organization_id,
                    Item.deleted_at.is_(None),
                )
                .first()
            )

            if item:
                template_id = getattr(item, template_field, None)
                if template_id:
                    template = self.get_by_id(template_id, organization_id)
                    if template and template.is_active:
                        if self._matches_applicability_rules(
                            template, customer_location, supplier_location
                        ):
                            return template, "item"

        # 2. Check item_group-level template
        if item_group_id:
            from app.models.item_group import ItemGroup

            item_group = (
                self.db.query(ItemGroup)
                .filter(
                    ItemGroup.id == item_group_id,
                    ItemGroup.organization_id == organization_id,
                    ItemGroup.deleted_at.is_(None),
                )
                .first()
            )

            if item_group:
                template_id = getattr(item_group, template_field, None)
                if template_id:
                    template = self.get_by_id(template_id, organization_id)
                    if template and template.is_active:
                        if self._matches_applicability_rules(
                            template, customer_location, supplier_location
                        ):
                            return template, "item_group"

        # 3. Check organization default template
        default_template = self.get_default_template(organization_id, tax_category)
        if default_template:
            if self._matches_applicability_rules(
                default_template, customer_location, supplier_location
            ):
                return default_template, "organization_default"

        return None

    def _matches_applicability_rules(
        self,
        template: TaxTemplate,
        customer_location: dict | None = None,
        supplier_location: dict | None = None,
    ) -> bool:
        """
        Check if template's applicability rules match the given context.

        Args:
            template: TaxTemplate to check
            customer_location: Optional customer location dict
            supplier_location: Optional supplier location dict

        Returns:
            True if all rules match (AND logic), False otherwise
        """
        if not template.applicability_rules:
            return True

        rules = template.applicability_rules

        # Check customer_location
        if "customer_location" in rules and customer_location:
            rule_location = rules["customer_location"]
            if not self._matches_location(rule_location, customer_location):
                return False

        # Check supplier_location
        if "supplier_location" in rules and supplier_location:
            rule_location = rules["supplier_location"]
            if not self._matches_location(rule_location, supplier_location):
                return False

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
            self.db.query(TaxTemplate)
            .filter(
                TaxTemplate.template_code == template_code,
                TaxTemplate.organization_id == organization_id,
                TaxTemplate.deleted_at.is_(None),
            )
            .count()
            > 0
        )

    def is_template_referenced(self, template_id: UUID, organization_id: UUID) -> dict:
        """
        Check if template is referenced by items, item_groups, or transactions.

        Args:
            template_id: Template UUID
            organization_id: Organization UUID

        Returns:
            Dictionary with lists of referencing entities
        """
        from app.models.item import Item
        from app.models.item_group import ItemGroup

        references = {"items": [], "item_groups": [], "transactions": []}

        # Check items
        items = (
            self.db.query(Item)
            .filter(
                Item.organization_id == organization_id,
                Item.deleted_at.is_(None),
                (Item.sales_tax_template_id == template_id)
                | (Item.purchase_tax_template_id == template_id),
            )
            .all()
        )
        references["items"] = [str(item.id) for item in items]

        # Check item_groups
        item_groups = (
            self.db.query(ItemGroup)
            .filter(
                ItemGroup.organization_id == organization_id,
                ItemGroup.deleted_at.is_(None),
                (ItemGroup.sales_tax_template_id == template_id)
                | (ItemGroup.purchase_tax_template_id == template_id),
            )
            .all()
        )
        references["item_groups"] = [str(group.id) for group in item_groups]

        # Check transactions (tax breakdown)
        from app.models.transaction_breakdown import TransactionTaxBreakdown

        transactions = (
            self.db.query(TransactionTaxBreakdown.transaction_id)
            .filter(
                TransactionTaxBreakdown.organization_id == organization_id,
                TransactionTaxBreakdown.tax_template_id == template_id,
            )
            .distinct()
            .all()
        )
        references["transactions"] = [str(t[0]) for t in transactions]

        return references
