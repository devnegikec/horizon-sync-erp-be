"""Service for bulk customer import operations"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.bulk_operations import FileParser
from app.models.customer import Customer
from app.services.document_numbering_service import DocumentNumberingService

logger = logging.getLogger(__name__)

# Valid columns for customer import CSV
VALID_CUSTOMER_COLUMNS = [
    "customer_name",
    "customer_code",
    "email",
    "phone",
    "address",
    "address_line1",
    "address_line2",
    "city",
    "state",
    "postal_code",
    "country",
    "tax_number",
    "status",
    "credit_limit",
]

REQUIRED_CUSTOMER_COLUMNS = ["customer_name"]


class BulkCustomerImportService:
    """Service for bulk customer import operations"""

    def __init__(self, db: Session):
        self.db = db

    def validate_row(self, row: dict, row_number: int) -> tuple[bool, list[str]]:
        """Validate a single customer row."""
        errors = []

        # Check required fields
        customer_name = row.get("customer_name", "").strip() if row.get("customer_name") else ""
        if not customer_name:
            errors.append(f"Row {row_number}: 'customer_name' is required")

        # Validate status if provided
        status_val = row.get("status", "").strip().lower() if row.get("status") else ""
        if status_val and status_val not in ("active", "inactive", "blocked"):
            errors.append(f"Row {row_number}: Invalid status '{status_val}'. Must be: active, inactive, blocked")

        # Validate credit_limit if provided
        credit_limit = row.get("credit_limit")
        if credit_limit is not None and credit_limit != "":
            try:
                val = float(credit_limit)
                if val < 0:
                    errors.append(f"Row {row_number}: credit_limit cannot be negative")
            except (ValueError, TypeError):
                errors.append(f"Row {row_number}: credit_limit must be a number")

        return len(errors) == 0, errors

    async def process_import(
        self,
        organization_id: UUID,
        user_id: UUID,
        file_content: bytes,
        file_format: str,
    ) -> dict:
        """
        Process bulk customer import file.

        Returns dict with: success, total_rows, successful_rows, failed_rows, errors
        """
        try:
            # Parse file
            try:
                rows = FileParser.parse_file(file_content, file_format)
            except ValueError as e:
                return {"success": False, "error": f"File parsing failed: {str(e)}",
                        "total_rows": 0, "successful_rows": 0, "failed_rows": 0}

            if not rows:
                return {"success": False, "error": "No data found in file",
                        "total_rows": 0, "successful_rows": 0, "failed_rows": 0}

            if len(rows) > 10000:
                return {"success": False, "error": f"File contains {len(rows)} rows. Maximum allowed is 10,000",
                        "total_rows": len(rows), "successful_rows": 0, "failed_rows": 0}

            # Validate columns
            file_columns = [c.lower().strip() for c in rows[0].keys()]
            if "customer_name" not in file_columns:
                return {"success": False, "error": "Required column 'customer_name' not found in file",
                        "total_rows": len(rows), "successful_rows": 0, "failed_rows": 0}

            successful_rows = 0
            failed_rows = 0
            error_details = []

            for row_number, row in enumerate(rows, start=1):
                # Normalize keys to lowercase
                normalized_row = {k.lower().strip(): v for k, v in row.items()}

                # Validate row
                is_valid, errors = self.validate_row(normalized_row, row_number)
                if not is_valid:
                    failed_rows += 1
                    error_details.append({"row_number": row_number, "errors": errors})
                    continue

                customer_name = normalized_row["customer_name"].strip()

                # Check if customer with same name already exists — update instead of create
                existing_customer = (
                    self.db.query(Customer)
                    .filter(
                        Customer.organization_id == organization_id,
                        Customer.customer_name == customer_name,
                        Customer.deleted_at.is_(None),
                    )
                    .first()
                )

                try:
                    customer_data = {
                        "customer_name": customer_name,
                        "updated_by": user_id,
                    }

                    # Map optional fields
                    optional_fields = [
                        "email", "phone", "address", "address_line1", "address_line2",
                        "city", "state", "postal_code", "country", "tax_number",
                    ]
                    for field in optional_fields:
                        val = normalized_row.get(field)
                        if val is not None and str(val).strip():
                            customer_data[field] = str(val).strip()

                    # Handle status
                    status_val = normalized_row.get("status", "").strip().lower() if normalized_row.get("status") else ""
                    if status_val:
                        customer_data["status"] = status_val

                    # Handle credit_limit
                    credit_limit = normalized_row.get("credit_limit")
                    if credit_limit is not None and str(credit_limit).strip():
                        try:
                            customer_data["credit_limit"] = float(credit_limit)
                        except (ValueError, TypeError):
                            pass

                    if existing_customer:
                        # Update existing customer
                        for key, value in customer_data.items():
                            if key != "customer_name":  # Don't update the name we matched on
                                setattr(existing_customer, key, value)
                        self.db.commit()
                    else:
                        # Auto-generate customer_code if not provided
                        customer_code = normalized_row.get("customer_code", "").strip() if normalized_row.get("customer_code") else ""
                        if not customer_code:
                            customer_code = DocumentNumberingService(self.db).get_next_number(
                                organization_id, "customer"
                            )
                        customer_data["customer_code"] = customer_code
                        customer_data["organization_id"] = organization_id
                        customer_data["created_by"] = user_id
                        if "status" not in customer_data:
                            customer_data["status"] = "active"

                        new_customer = Customer(**customer_data)
                        self.db.add(new_customer)
                        self.db.commit()

                    successful_rows += 1

                except Exception as e:
                    self.db.rollback()
                    failed_rows += 1
                    error_details.append({
                        "row_number": row_number,
                        "errors": [str(e)],
                    })
                    logger.error(f"Failed to import customer row {row_number}: {str(e)}")

            return {
                "success": True,
                "total_rows": len(rows),
                "successful_rows": successful_rows,
                "failed_rows": failed_rows,
                "errors": error_details if error_details else None,
                "status": "COMPLETED",
            }

        except Exception as e:
            logger.error(f"Bulk customer import failed: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e),
                    "total_rows": 0, "successful_rows": 0, "failed_rows": 0}
