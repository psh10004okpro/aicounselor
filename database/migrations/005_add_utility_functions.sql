-- Migration: 005_add_utility_functions.sql
-- Description: Add utility functions for common operations
-- Date: 2024-01-05
-- =============================================================================

-- Encryption functions
CREATE OR REPLACE FUNCTION encrypt_data(data TEXT, key TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN encode(pgp_sym_encrypt(data, key), 'base64');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION decrypt_data(encrypted TEXT, key TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(decode(encrypted, 'base64'), key);
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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

CREATE TRIGGER update_conversation_last_message
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_last_message();

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

-- Function to find similar messages
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

-- Data cleanup function for GDPR/HIPAA compliance
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
    -- Soft delete old conversations
    UPDATE conversations
    SET is_deleted = TRUE, deleted_at = CURRENT_TIMESTAMP
    WHERE created_at < CURRENT_TIMESTAMP - (retention_days || ' days')::INTERVAL
    AND is_deleted = FALSE;
    GET DIAGNOSTICS conversations_count = ROW_COUNT;

    -- Soft delete messages from deleted conversations
    UPDATE messages
    SET is_deleted = TRUE
    WHERE conversation_id IN (
        SELECT conversation_id FROM conversations WHERE is_deleted = TRUE
    )
    AND is_deleted = FALSE;
    GET DIAGNOSTICS messages_count = ROW_COUNT;

    -- Anonymize old user data
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

COMMENT ON FUNCTION encrypt_data IS 'Encrypt sensitive data using pgcrypto';
COMMENT ON FUNCTION decrypt_data IS 'Decrypt sensitive data using pgcrypto';
COMMENT ON FUNCTION find_similar_messages IS 'Find similar messages using vector similarity';
COMMENT ON FUNCTION get_relevant_memories IS 'Get relevant memories ranked by similarity and importance';
COMMENT ON FUNCTION cleanup_old_data IS 'GDPR/HIPAA compliant data cleanup';
