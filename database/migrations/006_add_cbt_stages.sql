-- =============================================================================
-- CBT Stage Tracking System Migration
-- Adds dynamic prompt system based on 6-stage CBT framework
-- =============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- TABLE: conversation_stages
-- Tracks the current CBT stage for each conversation
-- =============================================================================

CREATE TABLE IF NOT EXISTS conversation_stages (
    stage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,

    -- CBT Stage (1-6)
    current_stage INTEGER NOT NULL CHECK (current_stage BETWEEN 1 AND 6),
    stage_name VARCHAR(50) NOT NULL,
    -- Possible values: 'assessment', 'reconceptualization', 'skills_acquisition',
    --                  'skills_application', 'generalization', 'termination'

    -- Stage progress (0-100%)
    stage_progress INTEGER DEFAULT 0 CHECK (stage_progress BETWEEN 0 AND 100),

    -- Goals achieved in current stage
    goals_achieved JSONB DEFAULT '[]'::jsonb,
    -- Example: ["rapport_built", "problem_identified", "trust_established"]

    -- Goals still pending
    goals_pending JSONB DEFAULT '[]'::jsonb,
    -- Example: ["abc_model_understood", "cognitive_distortions_identified"]

    -- Readiness for next stage (0-100%)
    readiness_for_next_stage INTEGER DEFAULT 0 CHECK (readiness_for_next_stage BETWEEN 0 AND 100),

    -- Stage transition history
    stage_history JSONB DEFAULT '[]'::jsonb,
    -- Example: [
    --   {
    --     "stage": 1,
    --     "stage_name": "assessment",
    --     "entered_at": "2024-01-01T10:00:00Z",
    --     "exited_at": "2024-01-01T11:00:00Z",
    --     "progress": 100,
    --     "goals_achieved": ["rapport_built", "problem_identified"]
    --   }
    -- ]

    -- Current stage start time
    stage_started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Last assessment time
    last_assessed_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Constraints
    CONSTRAINT valid_stage_name CHECK (
        stage_name IN ('assessment', 'reconceptualization', 'skills_acquisition',
                      'skills_application', 'generalization', 'termination')
    ),

    -- One stage record per conversation
    CONSTRAINT unique_conversation_stage UNIQUE (conversation_id)
);

-- =============================================================================
-- TABLE: stage_assessments
-- Records automatic assessments of stage progress
-- =============================================================================

CREATE TABLE IF NOT EXISTS stage_assessments (
    assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    stage INTEGER NOT NULL CHECK (stage BETWEEN 1 AND 6),
    stage_name VARCHAR(50) NOT NULL,

    -- Assessment type
    assessment_type VARCHAR(50) NOT NULL DEFAULT 'automatic',
    -- Possible values: 'automatic', 'milestone', 'manual', 'transition'

    -- Assessment result from GPT-4
    assessment_result JSONB NOT NULL,
    -- Example:
    -- {
    --   "stage_progress": 75,
    --   "goals_achieved": ["rapport_built", "problem_identified"],
    --   "goals_pending": ["goals_established"],
    --   "readiness_for_next_stage": 80,
    --   "recommendation": "advance",
    --   "reasoning": "Client has established good rapport and identified main issues. Ready to move to reconceptualization.",
    --   "confidence": 0.85
    -- }

    -- Messages analyzed (count)
    messages_analyzed INTEGER DEFAULT 0,

    -- Assessment metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamp
    assessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Constraints
    CONSTRAINT valid_assessment_type CHECK (
        assessment_type IN ('automatic', 'milestone', 'manual', 'transition')
    )
);

-- =============================================================================
-- TABLE: stage_milestones
-- Defines milestones for each CBT stage
-- =============================================================================

CREATE TABLE IF NOT EXISTS stage_milestones (
    milestone_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stage INTEGER NOT NULL CHECK (stage BETWEEN 1 AND 6),
    stage_name VARCHAR(50) NOT NULL,

    -- Milestone details
    milestone_key VARCHAR(100) NOT NULL,
    milestone_name VARCHAR(255) NOT NULL,
    milestone_description TEXT,

    -- Milestone criteria
    criteria JSONB NOT NULL,
    -- Example:
    -- {
    --   "type": "keyword_detection",
    --   "keywords": ["understand", "makes sense"],
    --   "threshold": 3
    -- }

    -- Weight in stage progress (0-100)
    weight INTEGER DEFAULT 10 CHECK (weight BETWEEN 0 AND 100),

    -- Is this milestone required to advance?
    required_for_advancement BOOLEAN DEFAULT FALSE,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Constraints
    CONSTRAINT unique_milestone UNIQUE (stage, milestone_key)
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Conversation stages indexes
CREATE INDEX IF NOT EXISTS idx_conversation_stages_conversation_id
    ON conversation_stages(conversation_id);

CREATE INDEX IF NOT EXISTS idx_conversation_stages_current_stage
    ON conversation_stages(current_stage);

CREATE INDEX IF NOT EXISTS idx_conversation_stages_stage_name
    ON conversation_stages(stage_name);

CREATE INDEX IF NOT EXISTS idx_conversation_stages_updated_at
    ON conversation_stages(updated_at DESC);

-- JSONB indexes for goals
CREATE INDEX IF NOT EXISTS idx_conversation_stages_goals_achieved
    ON conversation_stages USING gin(goals_achieved);

CREATE INDEX IF NOT EXISTS idx_conversation_stages_goals_pending
    ON conversation_stages USING gin(goals_pending);

CREATE INDEX IF NOT EXISTS idx_conversation_stages_stage_history
    ON conversation_stages USING gin(stage_history);

-- Stage assessments indexes
CREATE INDEX IF NOT EXISTS idx_stage_assessments_conversation_id
    ON stage_assessments(conversation_id);

CREATE INDEX IF NOT EXISTS idx_stage_assessments_stage
    ON stage_assessments(stage);

CREATE INDEX IF NOT EXISTS idx_stage_assessments_assessed_at
    ON stage_assessments(assessed_at DESC);

CREATE INDEX IF NOT EXISTS idx_stage_assessments_type
    ON stage_assessments(assessment_type);

-- Stage milestones indexes
CREATE INDEX IF NOT EXISTS idx_stage_milestones_stage
    ON stage_milestones(stage);

CREATE INDEX IF NOT EXISTS idx_stage_milestones_required
    ON stage_milestones(required_for_advancement) WHERE required_for_advancement = TRUE;

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Update updated_at timestamp on conversation_stages
DROP TRIGGER IF EXISTS update_conversation_stages_updated_at ON conversation_stages;
CREATE TRIGGER update_conversation_stages_updated_at
    BEFORE UPDATE ON conversation_stages
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function to initialize CBT stage for a new conversation
CREATE OR REPLACE FUNCTION initialize_cbt_stage(conv_id UUID)
RETURNS UUID AS $$
DECLARE
    new_stage_id UUID;
BEGIN
    INSERT INTO conversation_stages (
        conversation_id,
        current_stage,
        stage_name,
        stage_progress,
        goals_pending
    ) VALUES (
        conv_id,
        1,
        'assessment',
        0,
        '["rapport_built", "problem_identified", "goals_established", "safe_environment"]'::jsonb
    )
    ON CONFLICT (conversation_id) DO NOTHING
    RETURNING stage_id INTO new_stage_id;

    RETURN new_stage_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get current stage for a conversation
CREATE OR REPLACE FUNCTION get_current_cbt_stage(conv_id UUID)
RETURNS TABLE(
    stage_id UUID,
    current_stage INTEGER,
    stage_name VARCHAR,
    stage_progress INTEGER,
    goals_achieved JSONB,
    goals_pending JSONB,
    readiness_for_next_stage INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        cs.stage_id,
        cs.current_stage,
        cs.stage_name,
        cs.stage_progress,
        cs.goals_achieved,
        cs.goals_pending,
        cs.readiness_for_next_stage
    FROM conversation_stages cs
    WHERE cs.conversation_id = conv_id;
END;
$$ LANGUAGE plpgsql;

-- Function to update stage progress
CREATE OR REPLACE FUNCTION update_stage_progress(
    conv_id UUID,
    new_progress INTEGER,
    new_goals_achieved JSONB,
    new_goals_pending JSONB,
    new_readiness INTEGER
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE conversation_stages
    SET
        stage_progress = new_progress,
        goals_achieved = new_goals_achieved,
        goals_pending = new_goals_pending,
        readiness_for_next_stage = new_readiness,
        last_assessed_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE conversation_id = conv_id;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to transition to next stage
CREATE OR REPLACE FUNCTION transition_to_next_stage(conv_id UUID)
RETURNS TABLE(
    success BOOLEAN,
    new_stage INTEGER,
    new_stage_name VARCHAR,
    message TEXT
) AS $$
DECLARE
    current_stage_rec RECORD;
    next_stage_num INTEGER;
    next_stage_nm VARCHAR;
    new_goals JSONB;
BEGIN
    -- Get current stage
    SELECT cs.current_stage, cs.stage_name, cs.stage_progress, cs.goals_achieved
    INTO current_stage_rec
    FROM conversation_stages cs
    WHERE cs.conversation_id = conv_id;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 0, ''::VARCHAR, 'Conversation stage not found'::TEXT;
        RETURN;
    END IF;

    -- Check if already at final stage
    IF current_stage_rec.current_stage = 6 THEN
        RETURN QUERY SELECT FALSE, 6, 'termination'::VARCHAR, 'Already at final stage'::TEXT;
        RETURN;
    END IF;

    -- Calculate next stage
    next_stage_num := current_stage_rec.current_stage + 1;

    -- Determine next stage name and goals
    next_stage_nm := CASE next_stage_num
        WHEN 2 THEN 'reconceptualization'
        WHEN 3 THEN 'skills_acquisition'
        WHEN 4 THEN 'skills_application'
        WHEN 5 THEN 'generalization'
        WHEN 6 THEN 'termination'
        ELSE 'assessment'
    END;

    new_goals := CASE next_stage_num
        WHEN 2 THEN '["abc_model_understood", "cognitive_distortions_identified", "thought_feeling_behavior_connection"]'::jsonb
        WHEN 3 THEN '["cognitive_restructuring_learned", "problem_solving_learned", "two_techniques_practiced"]'::jsonb
        WHEN 4 THEN '["technique_applied_reallife", "homework_completed", "obstacles_overcome"]'::jsonb
        WHEN 5 THEN '["progress_reviewed", "relapse_prevention_plan", "self_management_ready"]'::jsonb
        WHEN 6 THEN '["achievements_celebrated", "self_care_plan", "positive_closure"]'::jsonb
        ELSE '[]'::jsonb
    END;

    -- Update stage history
    UPDATE conversation_stages
    SET
        stage_history = stage_history || jsonb_build_object(
            'stage', current_stage_rec.current_stage,
            'stage_name', current_stage_rec.stage_name,
            'exited_at', CURRENT_TIMESTAMP,
            'progress', current_stage_rec.stage_progress,
            'goals_achieved', current_stage_rec.goals_achieved
        ),
        current_stage = next_stage_num,
        stage_name = next_stage_nm,
        stage_progress = 0,
        goals_achieved = '[]'::jsonb,
        goals_pending = new_goals,
        readiness_for_next_stage = 0,
        stage_started_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE conversation_id = conv_id;

    RETURN QUERY SELECT TRUE, next_stage_num, next_stage_nm, 'Successfully transitioned to next stage'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- INITIAL DATA: Stage Milestones
-- =============================================================================

-- Stage 1: Assessment milestones
INSERT INTO stage_milestones (stage, stage_name, milestone_key, milestone_name, milestone_description, weight, required_for_advancement) VALUES
(1, 'assessment', 'rapport_built', 'Rapport Built', 'Client shows trust and openness', 30, TRUE),
(1, 'assessment', 'problem_identified', 'Problem Identified', 'Main issues have been identified', 30, TRUE),
(1, 'assessment', 'goals_established', 'Goals Established', 'Client has set therapy goals', 25, TRUE),
(1, 'assessment', 'safe_environment', 'Safe Environment', 'Client feels safe and comfortable', 15, FALSE);

-- Stage 2: Reconceptualization milestones
INSERT INTO stage_milestones (stage, stage_name, milestone_key, milestone_name, milestone_description, weight, required_for_advancement) VALUES
(2, 'reconceptualization', 'abc_model_understood', 'ABC Model Understood', 'Client understands ABC model', 35, TRUE),
(2, 'reconceptualization', 'cognitive_distortions_identified', 'Cognitive Distortions Identified', 'Client can identify their distortions', 35, TRUE),
(2, 'reconceptualization', 'thought_feeling_behavior_connection', 'Thought-Feeling-Behavior Connection', 'Client sees the connection', 30, TRUE);

-- Stage 3: Skills Acquisition milestones
INSERT INTO stage_milestones (stage, stage_name, milestone_key, milestone_name, milestone_description, weight, required_for_advancement) VALUES
(3, 'skills_acquisition', 'cognitive_restructuring_learned', 'Cognitive Restructuring Learned', 'Client learned cognitive restructuring', 35, TRUE),
(3, 'skills_acquisition', 'problem_solving_learned', 'Problem Solving Learned', 'Client learned problem solving skills', 30, TRUE),
(3, 'skills_acquisition', 'two_techniques_practiced', 'Two Techniques Practiced', 'Client practiced at least 2 techniques', 35, TRUE);

-- Stage 4: Skills Application milestones
INSERT INTO stage_milestones (stage, stage_name, milestone_key, milestone_name, milestone_description, weight, required_for_advancement) VALUES
(4, 'skills_application', 'technique_applied_reallife', 'Technique Applied in Real Life', 'Client applied techniques outside therapy', 40, TRUE),
(4, 'skills_application', 'homework_completed', 'Homework Completed', 'Client completed homework assignments', 30, TRUE),
(4, 'skills_application', 'obstacles_overcome', 'Obstacles Overcome', 'Client overcame application difficulties', 30, FALSE);

-- Stage 5: Generalization milestones
INSERT INTO stage_milestones (stage, stage_name, milestone_key, milestone_name, milestone_description, weight, required_for_advancement) VALUES
(5, 'generalization', 'progress_reviewed', 'Progress Reviewed', 'Progress has been reviewed', 30, TRUE),
(5, 'generalization', 'relapse_prevention_plan', 'Relapse Prevention Plan', 'Relapse prevention plan created', 40, TRUE),
(5, 'generalization', 'self_management_ready', 'Self-Management Ready', 'Client ready for self-management', 30, TRUE);

-- Stage 6: Termination milestones
INSERT INTO stage_milestones (stage, stage_name, milestone_key, milestone_name, milestone_description, weight, required_for_advancement) VALUES
(6, 'termination', 'achievements_celebrated', 'Achievements Celebrated', 'Therapy achievements recognized', 35, TRUE),
(6, 'termination', 'self_care_plan', 'Self-Care Plan', 'Future self-care plan established', 35, TRUE),
(6, 'termination', 'positive_closure', 'Positive Closure', 'Therapy ended positively', 30, TRUE);

-- =============================================================================
-- COMMENTS FOR DOCUMENTATION
-- =============================================================================

COMMENT ON TABLE conversation_stages IS 'Tracks the current CBT stage for each conversation with progress and goals';
COMMENT ON TABLE stage_assessments IS 'Records automatic assessments of CBT stage progress using GPT-4';
COMMENT ON TABLE stage_milestones IS 'Defines milestones and criteria for each CBT stage';

COMMENT ON COLUMN conversation_stages.current_stage IS 'Current CBT stage (1=Assessment, 2=Reconceptualization, 3=Skills Acquisition, 4=Skills Application, 5=Generalization, 6=Termination)';
COMMENT ON COLUMN conversation_stages.stage_progress IS 'Progress in current stage (0-100%)';
COMMENT ON COLUMN conversation_stages.readiness_for_next_stage IS 'Readiness to advance to next stage (0-100%)';
COMMENT ON COLUMN conversation_stages.stage_history IS 'History of stage transitions with timestamps and achievements';

-- =============================================================================
-- SUCCESS MESSAGE
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '✅ CBT Stage Tracking System installed successfully!';
    RAISE NOTICE '';
    RAISE NOTICE '📊 Tables created:';
    RAISE NOTICE '   - conversation_stages: Track current CBT stage per conversation';
    RAISE NOTICE '   - stage_assessments: Record automatic progress assessments';
    RAISE NOTICE '   - stage_milestones: Define stage-specific goals and criteria';
    RAISE NOTICE '';
    RAISE NOTICE '🔧 Functions created:';
    RAISE NOTICE '   - initialize_cbt_stage(conversation_id): Initialize stage for new conversation';
    RAISE NOTICE '   - get_current_cbt_stage(conversation_id): Get current stage info';
    RAISE NOTICE '   - update_stage_progress(...): Update stage progress';
    RAISE NOTICE '   - transition_to_next_stage(conversation_id): Move to next stage';
    RAISE NOTICE '';
    RAISE NOTICE '🎯 6 CBT Stages configured:';
    RAISE NOTICE '   1. Assessment (초기 평가)';
    RAISE NOTICE '   2. Reconceptualization (재개념화)';
    RAISE NOTICE '   3. Skills Acquisition (기술 습득)';
    RAISE NOTICE '   4. Skills Application (기술 적용)';
    RAISE NOTICE '   5. Generalization (일반화 및 유지)';
    RAISE NOTICE '   6. Termination (종결)';
    RAISE NOTICE '';
    RAISE NOTICE '✨ Ready for dynamic prompt system!';
    RAISE NOTICE '';
END $$;
