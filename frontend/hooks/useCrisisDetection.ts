/**
 * useCrisisDetection Hook - Manages crisis detection UI state
 */

import { useState, useCallback, useEffect } from 'react'
import type { RiskLevel, CrisisAssessment } from '@/types/chat'

export interface UseCrisisDetectionOptions {
  onCrisisDetected?: (assessment: CrisisAssessment) => void
  autoDismiss?: boolean
  dismissTimeout?: number
}

export interface UseCrisisDetectionReturn {
  isVisible: boolean
  riskLevel: RiskLevel
  assessment: CrisisAssessment | null
  showCrisisAlert: (assessment: CrisisAssessment) => void
  dismissAlert: () => void
  resources: string[]
}

const KOREAN_RESOURCES = {
  critical: [
    { name: '자살예방상담전화', number: '1393', description: '24시간 무료 상담' },
    { name: '응급', number: '119', description: '생명이 위급한 경우' },
  ],
  high: [
    { name: '자살예방상담전화', number: '1393', description: '24시간 무료 상담' },
    { name: '청소년전화', number: '1388', description: '24시간 청소년 상담' },
    { name: '정신건강위기상담전화', number: '1577-0199', description: '24시간' },
  ],
  medium: [
    { name: '정신건강위기상담전화', number: '1577-0199', description: '24시간' },
    { name: '청소년전화', number: '1388', description: '24시간 청소년 상담' },
  ],
  low: [{ name: '정신건강위기상담전화', number: '1577-0199', description: '24시간' }],
  none: [],
}

export function useCrisisDetection(
  options: UseCrisisDetectionOptions = {}
): UseCrisisDetectionReturn {
  const [isVisible, setIsVisible] = useState(false)
  const [riskLevel, setRiskLevel] = useState<RiskLevel>('none')
  const [assessment, setAssessment] = useState<CrisisAssessment | null>(null)
  const [resources, setResources] = useState<string[]>([])

  // Auto-dismiss timer
  useEffect(() => {
    if (
      options.autoDismiss &&
      isVisible &&
      riskLevel !== 'critical' &&
      riskLevel !== 'high'
    ) {
      const timeout = setTimeout(() => {
        dismissAlert()
      }, options.dismissTimeout || 10000) // Default 10 seconds

      return () => clearTimeout(timeout)
    }
  }, [isVisible, riskLevel, options.autoDismiss, options.dismissTimeout])

  // Show crisis alert
  const showCrisisAlert = useCallback(
    (newAssessment: CrisisAssessment) => {
      setAssessment(newAssessment)
      setRiskLevel(newAssessment.risk_level)
      setIsVisible(true)

      // Set resources based on risk level
      const levelResources = KOREAN_RESOURCES[newAssessment.risk_level] || []
      setResources(levelResources.map((r) => r.number))

      // Call callback if provided
      options.onCrisisDetected?.(newAssessment)

      // Log to console for debugging
      console.warn('Crisis detected:', {
        level: newAssessment.risk_level,
        confidence: newAssessment.confidence,
        reasoning: newAssessment.reasoning,
        keywords: newAssessment.detected_keywords,
      })
    },
    [options]
  )

  // Dismiss alert
  const dismissAlert = useCallback(() => {
    setIsVisible(false)
    // Don't clear assessment immediately to allow for fade-out animations
    setTimeout(() => {
      setAssessment(null)
      setRiskLevel('none')
      setResources([])
    }, 300) // Match typical CSS transition duration
  }, [])

  return {
    isVisible,
    riskLevel,
    assessment,
    showCrisisAlert,
    dismissAlert,
    resources,
  }
}

/**
 * Get resource information for display
 */
export function getResourceInfo(riskLevel: RiskLevel) {
  return KOREAN_RESOURCES[riskLevel] || []
}

/**
 * Get urgent message based on risk level
 */
export function getUrgentMessage(riskLevel: RiskLevel): string {
  switch (riskLevel) {
    case 'critical':
      return '⚠️ 긴급 상황입니다. 지금 바로 아래 번호로 전화하거나 가까운 응급실을 방문하세요.'
    case 'high':
      return '힘든 시간을 보내고 계신 것 같습니다. 전문가의 도움을 받으시는 것을 권장합니다.'
    case 'medium':
      return '어려운 상황이신 것 같습니다. 필요하시면 언제든 전문 상담을 받으실 수 있습니다.'
    case 'low':
      return '힘드실 때 언제든 전문가의 도움을 받으실 수 있습니다.'
    default:
      return ''
  }
}
