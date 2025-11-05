-- Migration: 004_add_crisis_logs.sql
-- Description: Add crisis detection logging for safety monitoring
-- Date: 2024-01-04
-- =============================================================================

-- Create crisis_logs table
CREATE TABLE IF NOT EXISTS crisis_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(conversation_id) ON DELETE SET NULL,
    message_id UUID REFERENCES messages(message_id) ON DELETE SET NULL,

    -- Risk assessment
    risk_level VARCHAR(50) NOT NULL CHECK (risk_level IN ('none', 'low', 'medium', 'high', 'critical')),
    risk_score INTEGER CHECK (risk_score BETWEEN 0 AND 10),

    -- Crisis details
    message_content TEXT,
    detected_keywords JSONB,
    detection_method VARCHAR(100) CHECK (detection_method IN ('keyword', 'pattern', 'ml_model', 'combined')),

    -- Action taken
    action_taken VARCHAR(255),
    resources_provided JSONB,
    alert_sent BOOLEAN DEFAULT FALSE,
    alert_sent_to VARCHAR(255),

    -- Follow-up tracking
    follow_up_required BOOLEAN DEFAULT FALSE,
    follow_up_completed BOOLEAN DEFAULT FALSE,
    follow_up_notes TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for crisis monitoring
CREATE INDEX idx_crisis_logs_user_id ON crisis_logs(user_id);
CREATE INDEX idx_crisis_logs_conversation_id ON crisis_logs(conversation_id);
CREATE INDEX idx_crisis_logs_risk_level ON crisis_logs(risk_level);
CREATE INDEX idx_crisis_logs_created_at ON crisis_logs(created_at DESC);
CREATE INDEX idx_crisis_logs_unresolved ON crisis_logs(resolved_at) WHERE resolved_at IS NULL;
CREATE INDEX idx_crisis_logs_follow_up ON crisis_logs(follow_up_required)
    WHERE follow_up_required = TRUE AND follow_up_completed = FALSE;
CREATE INDEX idx_crisis_logs_user_risk_created ON crisis_logs(user_id, risk_level, created_at DESC);

COMMENT ON TABLE crisis_logs IS 'Crisis detection and intervention logging';
COMMENT ON COLUMN crisis_logs.risk_level IS 'Severity: none, low, medium, high, critical';
COMMENT ON COLUMN crisis_logs.detection_method IS 'How crisis was detected: keyword, pattern, ml_model, combined';
