-- Initialize PostgreSQL database with pgvector extension
-- This script runs automatically when the database is first created

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Create database (if running manually, otherwise created by Docker)
-- Note: This is typically handled by POSTGRES_DB environment variable in Docker

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE aicounselor TO postgres;

-- Log initialization
SELECT 'Database initialized with pgvector extension' AS status;
