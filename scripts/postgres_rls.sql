-- ==============================================================================
-- SRIVANI BOOKING MANAGER - PHASE 8 MULTI-TENANT ARCHITECTURE
-- PostgreSQL Defense-in-Depth: Row Level Security (RLS) Configuration
-- ==============================================================================
--
-- This script enables Row Level Security (RLS) on all tenant-owned tables.
-- The application sets session context per transaction:
--   SET LOCAL app.current_tenant_id = 'tenant-uuid-here';
--
-- Any database query executed within this transaction is automatically constrained
-- by the database engine itself to rows matching the current tenant ID, preventing
-- cross-tenant leakage even in raw SQL queries.
-- ==============================================================================

-- 1. FAMILIES TABLE
ALTER TABLE families ENABLE ROW LEVEL SECURITY;
ALTER TABLE families FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_families ON families;
CREATE POLICY tenant_isolation_families ON families
    FOR ALL
    USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::character varying
    )
    WITH CHECK (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::character varying
    );

-- 2. PILGRIMS TABLE
ALTER TABLE pilgrims ENABLE ROW LEVEL SECURITY;
ALTER TABLE pilgrims FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_pilgrims ON pilgrims;
CREATE POLICY tenant_isolation_pilgrims ON pilgrims
    FOR ALL
    USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::character varying
    )
    WITH CHECK (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::character varying
    );

-- 3. TICKET_FILES TABLE
ALTER TABLE ticket_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE ticket_files FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_ticket_files ON ticket_files;
CREATE POLICY tenant_isolation_ticket_files ON ticket_files
    FOR ALL
    USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::character varying
    )
    WITH CHECK (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::character varying
    );

-- 4. AUDIT_LOGS TABLE
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_audit_logs ON audit_logs;
CREATE POLICY tenant_isolation_audit_logs ON audit_logs
    FOR ALL
    USING (
        -- Allow tenant to read its own logs; platform admins can read with app.is_super_admin = 'true'
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::character varying
        OR current_setting('app.is_super_admin', true) = 'true'
    )
    WITH CHECK (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::character varying
        OR current_setting('app.is_super_admin', true) = 'true'
    );
