-- Initialize mindful AI counselor database
-- This script runs automatically when PostgreSQL container starts

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    is_anonymous BOOLEAN DEFAULT TRUE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    consent_given BOOLEAN DEFAULT FALSE,
    consent_timestamp TIMESTAMP,
    data_retention_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    summary TEXT,
    crisis_detected BOOLEAN DEFAULT FALSE,
    crisis_severity INTEGER DEFAULT 0,
    crisis_keywords_found JSONB,
    crisis_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP
);

-- Create messages table with vector embeddings
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI ada-002 embeddings
    token_count INTEGER,
    model_used VARCHAR(100),
    contains_crisis_keywords BOOLEAN DEFAULT FALSE,
    detected_keywords JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_session_token ON users(session_token);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_is_deleted ON users(is_deleted);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_last_message_at ON conversations(last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_crisis_detected ON conversations(crisis_detected);
CREATE INDEX IF NOT EXISTS idx_conversations_is_deleted ON conversations(is_deleted);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_crisis ON messages(contains_crisis_keywords);
CREATE INDEX IF NOT EXISTS idx_messages_is_deleted ON messages(is_deleted);

-- Create vector similarity search index (IVFFlat for better performance)
-- Note: This requires some data to be present before it can be created efficiently
-- For production, create this after loading initial data
-- CREATE INDEX IF NOT EXISTS idx_messages_embedding ON messages
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 100);

-- For development, use a simpler HNSW index (requires pg16+) or skip indexing
-- CREATE INDEX IF NOT EXISTS idx_messages_embedding ON messages
-- USING hnsw (embedding vector_cosine_ops);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to users table
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to conversations table
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to clean up old data (GDPR/HIPAA compliance)
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Soft delete conversations older than data retention period
    UPDATE conversations
    SET is_deleted = TRUE, deleted_at = CURRENT_TIMESTAMP
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '90 days'
    AND is_deleted = FALSE;

    -- Soft delete messages from deleted conversations
    UPDATE messages
    SET is_deleted = TRUE
    WHERE conversation_id IN (
        SELECT id FROM conversations WHERE is_deleted = TRUE
    )
    AND is_deleted = FALSE;

    -- Anonymize user data for deleted users
    UPDATE users
    SET
        email = NULL,
        session_token = 'deleted_' || id::text
    WHERE is_deleted = TRUE
    AND email IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Database initialized successfully!';
    RAISE NOTICE 'Tables created: users, conversations, messages';
    RAISE NOTICE 'pgvector extension enabled';
END $$;
