-- Additional tables for advanced features
-- Memories, summaries, and crisis logging

-- Memories table for long-term context
CREATE TABLE IF NOT EXISTS memories (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    memory_type VARCHAR(50) CHECK (memory_type IN ('semantic', 'episodic', 'fact')),
    content TEXT NOT NULL,
    embedding vector(1536),
    importance_score FLOAT CHECK (importance_score BETWEEN 0 AND 1),
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Conversation summaries for context compression
CREATE TABLE IF NOT EXISTS conversation_summaries (
    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    summary_embedding vector(1536),
    message_count INTEGER NOT NULL,
    start_message_id UUID,
    end_message_id UUID,
    keywords JSONB,
    sentiment_score FLOAT CHECK (sentiment_score BETWEEN -1 AND 1),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE,
    UNIQUE(conversation_id, created_at)
);

-- Crisis logs for safety monitoring
CREATE TABLE IF NOT EXISTS crisis_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    risk_level VARCHAR(20) CHECK (risk_level IN ('none', 'low', 'medium', 'high', 'critical')),
    detected_keywords JSONB,
    context_snippet TEXT,
    reasoning TEXT,
    confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 1),
    immediate_action_needed BOOLEAN DEFAULT FALSE,
    suggested_resources JSONB,
    action_taken VARCHAR(100),
    human_reviewed BOOLEAN DEFAULT FALSE,
    reviewer_notes TEXT,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for memories
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_conversation_id ON memories(conversation_id);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_is_deleted ON memories(is_deleted);

-- Indexes for conversation summaries
CREATE INDEX IF NOT EXISTS idx_summaries_conversation_id ON conversation_summaries(conversation_id);
CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON conversation_summaries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_summaries_is_deleted ON conversation_summaries(is_deleted);

-- Indexes for crisis logs
CREATE INDEX IF NOT EXISTS idx_crisis_logs_user_id ON crisis_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_crisis_logs_conversation_id ON crisis_logs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_crisis_logs_risk_level ON crisis_logs(risk_level);
CREATE INDEX IF NOT EXISTS idx_crisis_logs_detected_at ON crisis_logs(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_crisis_logs_action_needed ON crisis_logs(immediate_action_needed);
CREATE INDEX IF NOT EXISTS idx_crisis_logs_reviewed ON crisis_logs(human_reviewed);

-- Function to get relevant memories with importance scoring
CREATE OR REPLACE FUNCTION get_relevant_memories(
    p_user_id UUID,
    p_query_embedding vector(1536),
    p_memory_types VARCHAR[] DEFAULT NULL,
    p_min_importance FLOAT DEFAULT 0.3,
    p_max_results INTEGER DEFAULT 10
)
RETURNS TABLE (
    memory_id UUID,
    content TEXT,
    memory_type VARCHAR,
    importance_score FLOAT,
    similarity FLOAT,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.memory_id,
        m.content,
        m.memory_type,
        m.importance_score,
        1 - (m.embedding <=> p_query_embedding) AS similarity,
        m.created_at
    FROM memories m
    WHERE
        m.user_id = p_user_id
        AND m.is_deleted = FALSE
        AND (m.expires_at IS NULL OR m.expires_at > CURRENT_TIMESTAMP)
        AND m.importance_score >= p_min_importance
        AND (p_memory_types IS NULL OR m.memory_type = ANY(p_memory_types))
    ORDER BY
        (m.embedding <=> p_query_embedding) ASC,
        m.importance_score DESC
    LIMIT p_max_results;

    -- Update access count
    UPDATE memories m
    SET
        access_count = access_count + 1,
        last_accessed_at = CURRENT_TIMESTAMP
    WHERE m.memory_id IN (
        SELECT memory_id FROM memories
        WHERE user_id = p_user_id
        AND is_deleted = FALSE
        ORDER BY (embedding <=> p_query_embedding) ASC
        LIMIT p_max_results
    );
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Additional tables created successfully!';
    RAISE NOTICE 'Tables: memories, conversation_summaries, crisis_logs';
END $$;
