/**
 * Chat Types for Mindful AI Counselor
 */

export type RiskLevel = 'none' | 'low' | 'medium' | 'high' | 'critical'

export type MessageRole = 'user' | 'assistant' | 'system'

export interface Message {
  id: string
  role: MessageRole
  content: string
  timestamp: Date
  crisisDetected?: boolean
  riskLevel?: RiskLevel
  detectedKeywords?: string[]
}

export interface StreamChunk {
  content: string
  done: boolean
  conversation_id?: string
  crisis_detected?: boolean
  risk_level?: RiskLevel
}

export interface ChatResponse {
  conversation_id: string
  message: Message
  crisis_detected: boolean
  crisis_severity?: number
  risk_level?: RiskLevel
}

export interface Conversation {
  id: string
  title: string
  created_at: Date
  last_message_at: Date
  crisis_detected: boolean
  message_count?: number
}

export interface CrisisAssessment {
  risk_level: RiskLevel
  reasoning: string
  immediate_action_needed: boolean
  suggested_resources: string[]
  confidence: number
  detected_keywords: string[]
}

export interface User {
  id: string
  email?: string
  is_anonymous: boolean
  session_token: string
  consent_given: boolean
  created_at: Date
}

export interface AnonymousSessionResponse {
  user: User
  session_token: string
}

export interface ChatConfig {
  maxTokens?: number
  temperature?: number
  model?: string
}

export interface UseChatOptions {
  sessionToken?: string
  conversationId?: string | null
  onError?: (error: Error) => void
  onCrisisDetected?: (assessment: CrisisAssessment) => void
}

export interface UseChatReturn {
  messages: Message[]
  isLoading: boolean
  error: Error | null
  sendMessage: (content: string) => Promise<void>
  clearMessages: () => void
  conversationId: string | null
  crisisDetected: boolean
  riskLevel: RiskLevel
}

export interface ConsentData {
  consent_given: boolean
  consent_timestamp: Date
  user_id: string
}

// CBT Stage Types
export interface CBTStage {
  stage_number: number
  stage_name: string
  korean_name: string
}

export interface CBTProgress {
  current_stage: number
  stage_name: string
  stage_progress: number
  goals_achieved: string[]
  goals_pending: string[]
  readiness_for_next_stage: number
  stage_history?: Array<{
    from_stage: number
    to_stage: number
    transitioned_at: string
    goals_achieved: string[]
  }>
}

export interface CBTStageInfo {
  success: boolean
  conversation_id: string
  current_stage: CBTStage
  progress: CBTProgress
}

export interface CBTStageDescription {
  stage_number: number
  stage_name: string
  korean_name: string
  goals: string[]
  description: string
  system_prompt_preview?: string
}
