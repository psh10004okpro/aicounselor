-- Migration: 002_add_memories_table.sql
-- Description: Add memories table for long-term context management
-- Date: 2024-01-02
-- =============================================================================

-- Create memories table
CREATE TABLE IF NOT EXISTS memories (
    memory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Memory classification
    memory_type VARCHAR(50) NOT NULL CHECK (memory_type IN ('semantic', 'episodic', 'fact')),

    -- Content and embedding
    content TEXT NOT NULL,
    embedding vector(1536),

    -- Importance and access tracking
    importance_score FLOAT DEFAULT 0.5 CHECK (importance_score BETWEEN 0 AND 1),
    access_count INTEGER DEFAULT 0,
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
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Create indexes for memories
CREATE INDEX idx_memories_user_id ON memories(user_id) WHERE NOT is_deleted;
CREATE INDEX idx_memories_type ON memories(memory_type) WHERE NOT is_deleted;
CREATE INDEX idx_memories_importance ON memories(importance_score DESC) WHERE NOT is_deleted;
CREATE INDEX idx_memories_user_type_importance ON memories(user_id, memory_type, importance_score DESC) WHERE NOT is_deleted;

-- Vector index for similarity search
CREATE INDEX idx_memories_embedding ON memories
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50)
WHERE embedding IS NOT NULL AND NOT is_deleted;

-- Add trigger for updated_at
CREATE TRIGGER update_memories_updated_at
    BEFORE UPDATE ON memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE memories IS 'Long-term user memories for personalized context';
COMMENT ON COLUMN memories.memory_type IS 'semantic: facts, episodic: events, fact: user info';
COMMENT ON COLUMN memories.importance_score IS 'Relevance score (0-1) for prioritization';
