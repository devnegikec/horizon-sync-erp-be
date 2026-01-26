-- ===========================================
-- Create Invitations Table
-- ===========================================
-- Run this script to create the invitations table
--
-- Usage:
--   docker compose exec postgres psql -U horizon_user -d identity_db -f /app/scripts/create_invitations_table.sql
-- Note: Database is specified in the psql command, no need for \c

-- Create invitations table if not exists
CREATE TABLE IF NOT EXISTS invitations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role_id UUID REFERENCES roles(id) ON DELETE SET NULL,
    team_ids JSONB DEFAULT '[]',
    invited_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    accepted_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    message TEXT,
    extra_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_invitations_organization_id ON invitations(organization_id);
CREATE INDEX IF NOT EXISTS idx_invitations_email ON invitations(email);
CREATE INDEX IF NOT EXISTS idx_invitations_token_hash ON invitations(token_hash);
CREATE INDEX IF NOT EXISTS idx_invitations_status ON invitations(status);
CREATE INDEX IF NOT EXISTS idx_invitations_expires_at ON invitations(expires_at);

-- Add comment to table
COMMENT ON TABLE invitations IS 'Stores user invitations to organizations';

-- Verify table creation
SELECT 'Invitations table created successfully!' AS status;

-- Show table structure
\d invitations;
