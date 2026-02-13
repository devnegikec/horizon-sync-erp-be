"""Create search_documents and search_configurations tables

Revision ID: 001
Revises: 
Create Date: 2024-02-08 22:40:00.000000

This migration creates the core search tables with full-text search support:
- search_documents: Stores searchable content with tsvector for FTS
- search_configurations: Stores entity-specific search configurations

Requirements: 8.1, 8.4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create search tables with full-text search support"""
    
    # Create search_documents table
    op.create_table(
        'search_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('entity_id', 'entity_type', name='uq_entity_id_type'),
    )
    
    # Create indexes for search_documents
    # GIN index for full-text search on search_vector
    op.create_index(
        'idx_search_documents_vector',
        'search_documents',
        ['search_vector'],
        unique=False,
        postgresql_using='gin'
    )
    
    # Index on entity_id for lookups
    op.create_index(
        'idx_search_documents_entity_id',
        'search_documents',
        ['entity_id'],
        unique=False
    )
    
    # Index on entity_type for filtering
    op.create_index(
        'idx_search_documents_entity_type',
        'search_documents',
        ['entity_type'],
        unique=False
    )
    
    # Index on updated_at for synchronization queries
    op.create_index(
        'idx_search_documents_updated_at',
        'search_documents',
        ['updated_at'],
        unique=False
    )
    
    # Create generated column for search_vector using PostgreSQL function
    # This combines title (weight A), content (weight B), and metadata tags (weight C)
    op.execute("""
        ALTER TABLE search_documents 
        ADD COLUMN search_vector_generated tsvector 
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(content, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(metadata->>'tags', '')), 'C')
        ) STORED;
    """)
    
    # Drop the nullable search_vector column and rename the generated one
    op.drop_column('search_documents', 'search_vector')
    op.execute("ALTER TABLE search_documents RENAME COLUMN search_vector_generated TO search_vector")
    
    # Recreate the GIN index on the generated column
    op.execute("DROP INDEX IF EXISTS idx_search_documents_vector")
    op.create_index(
        'idx_search_documents_vector',
        'search_documents',
        ['search_vector'],
        unique=False,
        postgresql_using='gin'
    )
    
    # Create trigger to update updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_search_documents_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER trigger_update_search_documents_updated_at
        BEFORE UPDATE ON search_documents
        FOR EACH ROW
        EXECUTE FUNCTION update_search_documents_updated_at();
    """)
    
    # Create search_configurations table
    op.create_table(
        'search_configurations',
        sa.Column('entity_type', sa.String(), primary_key=True),
        sa.Column('searchable_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('boost_factors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('filters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    
    # Insert default search configurations for ERP entity types
    op.execute("""
        INSERT INTO search_configurations (entity_type, searchable_fields, boost_factors, filters) VALUES
        ('items', 
         '["item_code", "item_name", "description", "item_group"]'::jsonb,
         '{"item_code": 2.0, "item_name": 1.5, "description": 1.0}'::jsonb,
         '{"item_type": ["stock", "non_stock", "service", "fixed_asset"], "status": ["active", "inactive", "discontinued"]}'::jsonb
        ),
        ('customers', 
         '["customer_code", "customer_name", "email", "phone"]'::jsonb,
         '{"customer_code": 2.0, "customer_name": 1.5, "email": 1.2}'::jsonb,
         '{"status": ["active", "inactive"]}'::jsonb
        ),
        ('suppliers', 
         '["supplier_code", "supplier_name", "email", "phone"]'::jsonb,
         '{"supplier_code": 2.0, "supplier_name": 1.5, "email": 1.2}'::jsonb,
         '{"status": ["active", "inactive"]}'::jsonb
        ),
        ('warehouses', 
         '["warehouse_code", "warehouse_name", "location"]'::jsonb,
         '{"warehouse_code": 2.0, "warehouse_name": 1.5}'::jsonb,
         '{"warehouse_type": ["warehouse", "store", "virtual", "transit"]}'::jsonb
        ),
        ('stock_entries', 
         '["entry_number", "purpose", "remarks"]'::jsonb,
         '{"entry_number": 2.0, "purpose": 1.5}'::jsonb,
         '{"entry_type": ["material_receipt", "material_issue", "material_transfer"], "status": ["draft", "submitted", "cancelled"]}'::jsonb
        );
    """)


def downgrade() -> None:
    """Drop search tables"""
    
    # Drop triggers and functions
    op.execute("DROP TRIGGER IF EXISTS trigger_update_search_documents_updated_at ON search_documents")
    op.execute("DROP FUNCTION IF EXISTS update_search_documents_updated_at()")
    
    # Drop search_configurations table
    op.drop_table('search_configurations')
    
    # Drop indexes for search_documents
    op.drop_index('idx_search_documents_updated_at', table_name='search_documents')
    op.drop_index('idx_search_documents_entity_type', table_name='search_documents')
    op.drop_index('idx_search_documents_entity_id', table_name='search_documents')
    op.drop_index('idx_search_documents_vector', table_name='search_documents')
    
    # Drop search_documents table
    op.drop_table('search_documents')
