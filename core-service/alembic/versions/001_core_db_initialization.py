"""Initial baseline migration for core_db

Revision ID: 001_core_db_initialization
Revises: None
Create Date: 2026-02-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_core_db_initialization"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # This is a baseline migration that represents the existing schema
    # All tables (bulk_export_jobs, bulk_import_jobs, customers, item_groups, items, 
    # quotation_items, quotations, sales_order_items, sales_orders, warehouses_extended)
    # already exist in the database and are managed by other services
    pass

def downgrade() -> None:
    # This is a baseline migration - no downgrade needed
    pass
