-- FinSecAI PostgreSQL Initialization Script
-- Runs automatically on first container start

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search on prompts

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE findb TO finuser;

-- Log initialization
DO $$
BEGIN
  RAISE NOTICE 'FinSecAI database initialized successfully at %', NOW();
END $$;
