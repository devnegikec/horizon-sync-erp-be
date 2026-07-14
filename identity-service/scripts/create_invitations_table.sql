-- ===========================================
-- Create Invitations Table
-- ===========================================
-- Matches: schema.dbml (invitations) + Ref: invited_by_id>users, organization_id>organizations, role_id>roles
-- Used by: identity-service Invitations API (app/api/v1/endpoints/invitations.py)
--
-- Prerequisites: organizations, users, roles must exist.
-- Run after: init_db.sql (or equivalent that creates orgs/users/roles)
--
-- Usage:
--   docker compose exec postgres psql -U horizon_user -d identity_db -f /app/scripts/create_invitations_table.sql
--
-- Or from project root:
--   docker compose exec -T postgres psql -U horizon_user -d identity_db < identity-service/scripts/create_invitations_table.sql

-- ---------------------------------------------------------------------------
-- 1. Create invitations table
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS invitations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email               VARCHAR(255) NOT NULL,
    first_name          VARCHAR(100),
    last_name           VARCHAR(100),
    role_id             UUID REFERENCES roles(id) ON DELETE SET NULL,
    team_ids            JSONB DEFAULT '[]',
    invited_by_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    token_hash          VARCHAR(255) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'pending',
    expires_at          TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at         TIMESTAMP WITH TIME ZONE,
    accepted_user_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    message             TEXT,
    extra_data          JSONB DEFAULT '{}',
    CONSTRAINT uq_invitations_token_hash UNIQUE (token_hash)
);

-- ---------------------------------------------------------------------------
-- 2. Indexes (for list, lookup, and token/status filters)
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_invitations_organization_id   ON invitations(organization_id);
CREATE INDEX IF NOT EXISTS idx_invitations_email             ON invitations(email);
CREATE INDEX IF NOT EXISTS idx_invitations_status            ON invitations(status);
CREATE INDEX IF NOT EXISTS idx_invitations_expires_at        ON invitations(expires_at);
CREATE INDEX IF NOT EXISTS idx_invitations_org_status        ON invitations(organization_id, status);
CREATE INDEX IF NOT EXISTS idx_invitations_org_created       ON invitations(organization_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- 3. Comments
-- ---------------------------------------------------------------------------
COMMENT ON TABLE invitations IS 'User invitations to organizations; used by Invitations API.';
COMMENT ON COLUMN invitations.token_hash  IS 'Hashed token for /invitations/validate/{token} and /invitations/accept';
COMMENT ON COLUMN invitations.status      IS 'pending | accepted | expired | cancelled';
COMMENT ON COLUMN invitations.team_ids    IS 'JSON array of team UUIDs';

-- ---------------------------------------------------------------------------
-- 4. Verify
-- ---------------------------------------------------------------------------
SELECT 'Invitations table created successfully.' AS status;
