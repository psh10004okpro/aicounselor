-- =============================================================================
-- Mindful AI Counselor - Complete Database Schema
-- PostgreSQL 15+ with pgvector extension
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =============================================================================
-- ENCRYPTION FUNCTIONS
-- =============================================================================

-- Function to encrypt sensitive data
CREATE OR REPLACE FUNCTION encrypt_data(data TEXT, key TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN encode(pgp_sym_encrypt(data, key), 'base64');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to decrypt sensitive data
CREATE OR REPLACE FUNCTION decrypt_data(encrypted TEXT, key TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(decode(encrypted, 'base64'), key);
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- =============================================================================
-- TABLE: users
-- =============================================================================

CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Encrypted email for privacy compliance
    email_encrypted TEXT,
    email_hash VARCHAR(64) UNIQUE, -- For lookups without decryption

    -- Anonymous session support
    is_anonymous BOOLEAN DEFAULT TRUE,
    session_token VARCHAR(255) UNIQUE NOT NULL,

    -- Compliance fields
    consent_given BOOLEAN DEFAULT FALSE,
    consent_timestamp TIMESTAMP WITH TIME ZONE,
    data_retention_until TIMESTAMP WITH TIME ZONE,

    -- Metadata (user preferences, settings)
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Soft delete
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT valid_consent CHECK (
        (consent_given = FALSE) OR
        (consent_given = TRUE AND consent_timestamp IS NOT NULL)
    )
);

-- =============================================================================
-- TABLE: conversations
-- =============================================================================

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Conversation details
    title VARCHAR(255),
    summary TEXT,

    -- Status tracking
    status VARCHAR(50) DEFAULT 'active' NOT NULL,
    -- Possible values: 'active', 'archived', 'closed', 'flagged'

    -- Crisis detection
    crisis_detected BOOLEAN DEFAULT FALSE,
    crisis_severity INTEGER DEFAULT 0 CHECK (crisis_severity BETWEEN 0 AND 10),
    crisis_keywords_found JSONB,
    crisis_timestamp TIMESTAMP WITH TIME ZONE,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Soft delete
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT valid_status CHECK (
        status IN ('active', 'archived', 'closed', 'flagged')
    )
);

-- =============================================================================
-- TABLE: messages
-- =============================================================================

CREATE TABLE IF NOT EXISTS messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,

    -- Message details
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),

    -- Content (can be encrypted for sensitive data)
    content TEXT NOT NULL,
    content_encrypted TEXT, -- Optional encrypted version
    is_encrypted BOOLEAN DEFAULT FALSE,

    -- Vector embedding for semantic search (OpenAI ada-002: 1536 dimensions)
    embedding vector(1536),

    -- Token tracking
    tokens_used INTEGER,
    model_used VARCHAR(100),

    -- Crisis detection for this message
    contains_crisis_keywords BOOLEAN DEFAULT FALSE,
    detected_keywords JSONB,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Soft delete
    is_deleted BOOLEAN DEFAULT FALSE
);

-- =============================================================================
-- TABLE: memories
-- =============================================================================

CREATE TABLE IF NOT EXISTS memories (
    memory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Memory classification
    memory_type VARCHAR(50) NOT NULL,
    -- Types: 'semantic' (facts), 'episodic' (events), 'fact' (user info)

    -- Memory content
    content TEXT NOT NULL,
    embedding vector(1536), -- For similarity search

    -- Importance and relevance
    importance_score FLOAT DEFAULT 0.5 CHECK (importance_score BETWEEN 0 AND 1),
    access_count INTEGER DEFAULT 0, -- How many times accessed
    last_accessed_at TIMESTAMP WITH TIME ZONE,

    -- Source tracking
    source_conversation_id UUID REFERENCES conversations(conversation_id) ON DELETE SET NULL,
    source_message_id UUID REFERENCES messages(message_id) ON DELETE SET NULL,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Soft delete
    is_deleted BOOLEAN DEFAULT FALSE,

    -- Constraints
    CONSTRAINT valid_memory_type CHECK (
        memory_type IN ('semantic', 'episodic', 'fact')
    )
);

-- =============================================================================
-- TABLE: conversation_summaries
-- =============================================================================

CREATE TABLE IF NOT EXISTS conversation_summaries (
    summary_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,

    -- Summary details
    summary_text TEXT NOT NULL,
    summary_type VARCHAR(50) DEFAULT 'auto',
    -- Types: 'auto' (AI-generated), 'manual', 'periodic'

    -- Efficiency metrics
    tokens_saved INTEGER DEFAULT 0,
    original_message_count INTEGER,
    compression_ratio FLOAT, -- tokens_saved / original_tokens

    -- Summary metadata
    key_topics JSONB, -- Array of main topics discussed
    sentiment_score FLOAT CHECK (sentiment_score BETWEEN -1 AND 1),

    -- Embeddings for the summary
    embedding vector(1536),

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Constraints
    CONSTRAINT valid_summary_type CHECK (
        summary_type IN ('auto', 'manual', 'periodic')
    )
);

-- =============================================================================
-- TABLE: crisis_logs
-- =============================================================================

CREATE TABLE IF NOT EXISTS crisis_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(conversation_id) ON DELETE SET NULL,
    message_id UUID REFERENCES messages(message_id) ON DELETE SET NULL,

    -- Risk assessment
    risk_level VARCHAR(50) NOT NULL,
    -- Levels: 'none', 'low', 'medium', 'high', 'critical'
    risk_score INTEGER CHECK (risk_score BETWEEN 0 AND 10),

    -- Crisis details
    message_content TEXT, -- Snapshot of concerning content
    detected_keywords JSONB, -- Keywords that triggered alert
    detection_method VARCHAR(100), -- 'keyword', 'pattern', 'ml_model'

    -- Action taken
    action_taken VARCHAR(255),
    resources_provided JSONB, -- Crisis resources shown to user
    alert_sent BOOLEAN DEFAULT FALSE,
    alert_sent_to VARCHAR(255), -- Email/phone where alert was sent

    -- Follow-up
    follow_up_required BOOLEAN DEFAULT FALSE,
    follow_up_completed BOOLEAN DEFAULT FALSE,
    follow_up_notes TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT valid_risk_level CHECK (
        risk_level IN ('none', 'low', 'medium', 'high', 'critical')
    ),
    CONSTRAINT valid_detection_method CHECK (
        detection_method IN ('keyword', 'pattern', 'ml_model', 'combined')
    )
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Users table indexes
CREATE INDEX IF NOT EXISTS idx_users_session_token ON users(session_token) WHERE NOT is_deleted;
CREATE INDEX IF NOT EXISTS idx_users_email_hash ON users(email_hash) WHERE NOT is_deleted;
CREATE INDEX IF NOT EXISTS idx_users_is_deleted ON users(is_deleted);
CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active DESC) WHERE NOT is_deleted;
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);

-- Conversations table indexes
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id) WHERE NOT is_deleted;
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status) WHERE NOT is_deleted;
CREATE INDEX IF NOT EXISTS idx_conversations_last_message_at ON conversations(last_message_at DESC) WHERE NOT is_deleted;
CREATE INDEX IF NOT EXISTS idx_conversations_crisis_detected ON conversations(crisis_detected) WHERE crisis_detected = TRUE;
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_is_deleted ON conversations(is_deleted);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_conversations_user_status ON conversations(user_id, status, last_message_at DESC) WHERE NOT is_deleted;

-- Messages table indexes
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id) WHERE NOT is_deleted;
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);
CREATE INDEX IF NOT EXISTS idx_messages_crisis ON messages(contains_crisis_keywords) WHERE contains_crisis_keywords = TRUE;
CREATE INDEX IF NOT EXISTS idx_messages_is_deleted ON messages(is_deleted);

-- Composite index for conversation message retrieval
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created ON messages(conversation_id, created_at DESC) WHERE NOT is_deleted;

-- Vector similarity search index (HNSW - requires PostgreSQL 16+)
-- For PostgreSQL 15, use IVFFlat instead
-- Note: Create this after inserting some data for better performance

-- HNSW index (PostgreSQL 16+, more accurate but requires more memory)
-- CREATE INDEX IF NOT EXISTS idx_messages_embedding_hnsw ON messages
-- USING hnsw (embedding vector_cosine_ops)
-- WITH (m = 16, ef_construction = 64);

-- IVFFlat index (PostgreSQL 15, faster but requires training)
-- CREATE INDEX IF NOT EXISTS idx_messages_embedding_ivfflat ON messages
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 100);

-- For now, use a simpler index that works on both versions
CREATE INDEX IF NOT EXISTS idx_messages_embedding ON messages
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100)
WHERE embedding IS NOT NULL AND NOT is_deleted;

-- Memories table indexes
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id) WHERE NOT is_deleted;
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type) WHERE NOT is_deleted;
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance_score DESC) WHERE NOT is_deleted;
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_is_deleted ON memories(is_deleted);
CREATE INDEX IF NOT EXISTS idx_memories_access_count ON memories(access_count DESC) WHERE NOT is_deleted;

-- Composite index for memory retrieval
CREATE INDEX IF NOT EXISTS idx_memories_user_type_importance ON memories(user_id, memory_type, importance_score DESC) WHERE NOT is_deleted;

-- Vector index for memories
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50)
WHERE embedding IS NOT NULL AND NOT is_deleted;

-- Conversation summaries indexes
CREATE INDEX IF NOT EXISTS idx_summaries_conversation_id ON conversation_summaries(conversation_id);
CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON conversation_summaries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_summaries_type ON conversation_summaries(summary_type);

-- Vector index for summaries
CREATE INDEX IF NOT EXISTS idx_summaries_embedding ON conversation_summaries
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50)
WHERE embedding IS NOT NULL;

-- Crisis logs indexes
CREATE INDEX IF NOT EXISTS idx_crisis_logs_user_id ON crisis_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_crisis_logs_conversation_id ON crisis_logs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_crisis_logs_risk_level ON crisis_logs(risk_level);
CREATE INDEX IF NOT EXISTS idx_crisis_logs_created_at ON crisis_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crisis_logs_unresolved ON crisis_logs(resolved_at) WHERE resolved_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_crisis_logs_follow_up ON crisis_logs(follow_up_required) WHERE follow_up_required = TRUE AND follow_up_completed = FALSE;

-- Composite index for crisis monitoring
CREATE INDEX IF NOT EXISTS idx_crisis_logs_user_risk_created ON crisis_logs(user_id, risk_level, created_at DESC);

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Trigger function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply to conversations table
DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply to memories table
DROP TRIGGER IF EXISTS update_memories_updated_at ON memories;
CREATE TRIGGER update_memories_updated_at
    BEFORE UPDATE ON memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger to update conversation's last_message_at
CREATE OR REPLACE FUNCTION update_conversation_last_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations
    SET last_message_at = NEW.created_at
    WHERE conversation_id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_conversation_last_message ON messages;
CREATE TRIGGER update_conversation_last_message
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_last_message();

-- =============================================================================
-- UTILITY FUNCTIONS
-- =============================================================================

-- Function to calculate conversation token usage
CREATE OR REPLACE FUNCTION get_conversation_token_usage(conv_id UUID)
RETURNS INTEGER AS $$
DECLARE
    total_tokens INTEGER;
BEGIN
    SELECT COALESCE(SUM(tokens_used), 0)
    INTO total_tokens
    FROM messages
    WHERE conversation_id = conv_id AND NOT is_deleted;

    RETURN total_tokens;
END;
$$ LANGUAGE plpgsql;

-- Function to get similar messages using vector search
CREATE OR REPLACE FUNCTION find_similar_messages(
    query_embedding vector(1536),
    conv_id UUID DEFAULT NULL,
    similarity_threshold FLOAT DEFAULT 0.8,
    max_results INTEGER DEFAULT 5
)
RETURNS TABLE(
    message_id UUID,
    content TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.message_id,
        m.content,
        1 - (m.embedding <=> query_embedding) AS similarity
    FROM messages m
    WHERE
        m.embedding IS NOT NULL
        AND NOT m.is_deleted
        AND (conv_id IS NULL OR m.conversation_id = conv_id)
        AND (1 - (m.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY m.embedding <=> query_embedding
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Function to get relevant memories
CREATE OR REPLACE FUNCTION get_relevant_memories(
    query_embedding vector(1536),
    usr_id UUID,
    memory_types VARCHAR[] DEFAULT NULL,
    min_importance FLOAT DEFAULT 0.3,
    max_results INTEGER DEFAULT 10
)
RETURNS TABLE(
    memory_id UUID,
    memory_type VARCHAR,
    content TEXT,
    importance_score FLOAT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.memory_id,
        m.memory_type,
        m.content,
        m.importance_score,
        1 - (m.embedding <=> query_embedding) AS similarity
    FROM memories m
    WHERE
        m.user_id = usr_id
        AND m.embedding IS NOT NULL
        AND NOT m.is_deleted
        AND m.importance_score >= min_importance
        AND (memory_types IS NULL OR m.memory_type = ANY(memory_types))
    ORDER BY
        (1 - (m.embedding <=> query_embedding)) * m.importance_score DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Function for GDPR/HIPAA compliance - cleanup old data
CREATE OR REPLACE FUNCTION cleanup_old_data(retention_days INTEGER DEFAULT 90)
RETURNS TABLE(
    users_deleted INTEGER,
    conversations_deleted INTEGER,
    messages_deleted INTEGER
) AS $$
DECLARE
    users_count INTEGER;
    conversations_count INTEGER;
    messages_count INTEGER;
BEGIN
    -- Soft delete conversations older than retention period
    UPDATE conversations
    SET is_deleted = TRUE, deleted_at = CURRENT_TIMESTAMP
    WHERE created_at < CURRENT_TIMESTAMP - (retention_days || ' days')::INTERVAL
    AND is_deleted = FALSE
    RETURNING conversation_id INTO conversations_count;

    GET DIAGNOSTICS conversations_count = ROW_COUNT;

    -- Soft delete messages from deleted conversations
    UPDATE messages
    SET is_deleted = TRUE
    WHERE conversation_id IN (
        SELECT conversation_id FROM conversations WHERE is_deleted = TRUE
    )
    AND is_deleted = FALSE;

    GET DIAGNOSTICS messages_count = ROW_COUNT;

    -- Anonymize user data for users past retention
    UPDATE users
    SET
        email_encrypted = NULL,
        email_hash = NULL,
        is_deleted = TRUE,
        deleted_at = CURRENT_TIMESTAMP
    WHERE created_at < CURRENT_TIMESTAMP - (retention_days || ' days')::INTERVAL
    AND is_deleted = FALSE;

    GET DIAGNOSTICS users_count = ROW_COUNT;

    RETURN QUERY SELECT users_count, conversations_count, messages_count;
END;
$$ LANGUAGE plpgsql;

-- Function to archive old conversations
CREATE OR REPLACE FUNCTION archive_old_conversations(days_inactive INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    UPDATE conversations
    SET status = 'archived'
    WHERE
        status = 'active'
        AND last_message_at < CURRENT_TIMESTAMP - (days_inactive || ' days')::INTERVAL
        AND NOT is_deleted;

    GET DIAGNOSTICS archived_count = ROW_COUNT;
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- INITIAL DATA / SYSTEM CONFIGURATION
-- =============================================================================

-- Create a system user for automated tasks
INSERT INTO users (
    user_id,
    session_token,
    is_anonymous,
    metadata
) VALUES (
    '00000000-0000-0000-0000-000000000000',
    'system_user_token',
    FALSE,
    '{"role": "system", "description": "System user for automated tasks"}'::jsonb
) ON CONFLICT (user_id) DO NOTHING;

-- =============================================================================
-- PERMISSIONS (for production)
-- =============================================================================

-- Grant necessary permissions to application user
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_user;

-- =============================================================================
-- COMMENTS FOR DOCUMENTATION
-- =============================================================================

COMMENT ON TABLE users IS 'User accounts with privacy-focused design (email encryption, GDPR compliance)';
COMMENT ON TABLE conversations IS 'Conversation sessions between users and AI counselor';
COMMENT ON TABLE messages IS 'Individual messages with vector embeddings for semantic search';
COMMENT ON TABLE memories IS 'Long-term user memories for personalized context (semantic, episodic, facts)';
COMMENT ON TABLE conversation_summaries IS 'AI-generated summaries for token efficiency';
COMMENT ON TABLE crisis_logs IS 'Crisis detection and intervention logging for safety monitoring';

COMMENT ON COLUMN users.email_encrypted IS 'Encrypted email using pgcrypto for HIPAA compliance';
COMMENT ON COLUMN messages.embedding IS 'OpenAI ada-002 embedding (1536 dimensions) for semantic search';
COMMENT ON COLUMN memories.importance_score IS 'Relevance score (0-1) for memory prioritization';
COMMENT ON COLUMN conversation_summaries.compression_ratio IS 'Token efficiency: tokens_saved / original_tokens';

-- =============================================================================
-- SUCCESS MESSAGE
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Database schema created successfully!';
    RAISE NOTICE '📊 Tables: users, conversations, messages, memories, conversation_summaries, crisis_logs';
    RAISE NOTICE '🔍 Vector indexes created for semantic search';
    RAISE NOTICE '🔐 Encryption functions available';
    RAISE NOTICE '⚡ Performance indexes optimized';
    RAISE NOTICE '🛡️  HIPAA/GDPR compliance features enabled';
END $$;
