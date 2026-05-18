-- ═══════════════════════════════════════
--  Finsio PostgreSQL Initialization
--  Runs on first container start
-- ═══════════════════════════════════════

-- Required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set timezone
ALTER DATABASE finsio SET timezone TO 'UTC';

-- Log success
DO $$
BEGIN
    RAISE NOTICE 'Finsio database initialized successfully';
END $$;
