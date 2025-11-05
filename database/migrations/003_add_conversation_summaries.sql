-- Migration: 003_add_conversation_summaries.sql
-- Description: Add conversation summaries for token efficiency
-- Date: 2024-01-03
-- =============================================================================

-- Create conversation_summaries table
CREATE TABLE IF NOT EXISTS conversation_summaries (
    summary_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,

    -- Summary content
    summary_text TEXT NOT NULL,
    summary_type VARCHAR(50) DEFAULT 'auto' CHECK (summary_type IN ('auto', 'manual', 'periodic')),

    -- Efficiency metrics
    tokens_saved INTEGER DEFAULT 0,
    original_message_count INTEGER,
    compression_ratio FLOAT,

    -- Summary metadata
    key_topics JSONB,
    sentiment_score FLOAT CHECK (sentiment_score BETWEEN -1 AND 1),

    -- Embedding for semantic search
    embedding vector(1536),

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes
CREATE INDEX idx_summaries_conversation_id ON conversation_summaries(conversation_id);
CREATE INDEX idx_summaries_created_at ON conversation_summaries(created_at DESC);
CREATE INDEX idx_summaries_type ON conversation_summaries(summary_type);

-- Vector index
CREATE INDEX idx_summaries_embedding ON conversation_summaries
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50)
WHERE embedding IS NOT NULL;

COMMENT ON TABLE conversation_summaries IS 'AI-generated conversation summaries for token efficiency';
COMMENT ON COLUMN conversation_summaries.compression_ratio IS 'tokens_saved / original_tokens';
COMMENT ON COLUMN conversation_summaries.key_topics IS 'Array of main topics discussed';
