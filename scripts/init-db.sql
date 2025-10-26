-- Brain MVP Database Initialization
-- Create extensions if they don't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Note: vector extension may not be available in all PostgreSQL installations
-- CREATE EXTENSION IF NOT EXISTS "vector";

-- Basic database setup
-- Application will handle table creation through migrations
SELECT 'Brain MVP Database Initialized' as status;