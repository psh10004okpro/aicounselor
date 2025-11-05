'use client'

import { useCBTStage } from '@/hooks/useCBTStage'

interface CBTStageIndicatorProps {
  conversationId: string | null
  refreshInterval?: number
}

/**
 * CBT Stage Indicator Component
 *
 * Displays the current CBT therapy stage and progress for a conversation
 */
export default function CBTStageIndicator({
  conversationId,
  refreshInterval = 30000, // Default: refresh every 30 seconds
}: CBTStageIndicatorProps) {
  const { currentStage, progress, isLoading, error } = useCBTStage({
    conversationId,
    enabled: !!conversationId,
    refreshInterval,
  })

  // Don't render if no conversation or error
  if (!conversationId || error) {
    return null
  }

  // Loading state
  if (isLoading && !currentStage) {
    return (
      <div className="bg-gradient-to-r from-green-50 to-blue-50 border-l-4 border-green-500 p-4 rounded-lg animate-pulse">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gray-200 rounded-full"></div>
          <div className="flex-1">
            <div className="h-4 bg-gray-200 rounded w-1/3 mb-2"></div>
            <div className="h-3 bg-gray-200 rounded w-1/2"></div>
          </div>
        </div>
      </div>
    )
  }

  // No stage data
  if (!currentStage || !progress) {
    return null
  }

  // Calculate progress percentage
  const progressPercentage = progress.stage_progress || 0
  const readinessPercentage = progress.readiness_for_next_stage || 0

  // Stage color based on stage number
  const getStageColor = (stageNumber: number) => {
    const colors = [
      'bg-blue-500',    // Stage 1: Assessment
      'bg-indigo-500',  // Stage 2: Reconceptualization
      'bg-purple-500',  // Stage 3: Skills Acquisition
      'bg-pink-500',    // Stage 4: Skills Application
      'bg-rose-500',    // Stage 5: Generalization
      'bg-green-500',   // Stage 6: Termination
    ]
    return colors[stageNumber - 1] || 'bg-gray-500'
  }

  const stageColor = getStageColor(currentStage.stage_number)

  return (
    <div className="bg-gradient-to-r from-green-50 to-blue-50 border-l-4 border-green-500 p-4 rounded-lg shadow-sm">
      {/* Stage Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <div className={`w-10 h-10 ${stageColor} text-white rounded-full flex items-center justify-center font-bold text-lg shadow-md`}>
            {currentStage.stage_number}
          </div>
          <div>
            <h3 className="text-sm font-bold text-gray-800">
              {currentStage.korean_name}
            </h3>
            <p className="text-xs text-gray-600">
              {currentStage.stage_name}
            </p>
          </div>
        </div>

        {/* Stage Progress Badge */}
        <div className="text-right">
          <div className="text-xs text-gray-500 mb-1">단계 진행도</div>
          <div className="text-lg font-bold text-green-600">
            {progressPercentage}%
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-3">
        <div className="flex justify-between items-center mb-1">
          <span className="text-xs text-gray-600">현재 단계 진행 상황</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
          <div
            className={`h-2.5 ${stageColor} rounded-full transition-all duration-500 ease-out`}
            style={{ width: `${progressPercentage}%` }}
          ></div>
        </div>
      </div>

      {/* Goals Summary */}
      {progress.goals_achieved.length > 0 && (
        <div className="mb-2">
          <div className="flex items-center text-xs text-gray-600 mb-1">
            <svg
              className="w-4 h-4 text-green-500 mr-1"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            달성한 목표: {progress.goals_achieved.length}개
          </div>
        </div>
      )}

      {/* Pending Goals */}
      {progress.goals_pending.length > 0 && (
        <div className="mb-2">
          <div className="flex items-center text-xs text-gray-600">
            <svg
              className="w-4 h-4 text-amber-500 mr-1"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                clipRule="evenodd"
              />
            </svg>
            진행 중인 목표: {progress.goals_pending.length}개
          </div>
        </div>
      )}

      {/* Next Stage Readiness */}
      {readinessPercentage >= 70 && currentStage.stage_number < 6 && (
        <div className="mt-3 pt-3 border-t border-green-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center text-xs text-green-700">
              <svg
                className="w-4 h-4 text-green-600 mr-1"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z"
                  clipRule="evenodd"
                />
              </svg>
              다음 단계 준비도: {readinessPercentage}%
            </div>
            {readinessPercentage >= 80 && (
              <span className="text-xs font-semibold text-green-600 bg-green-100 px-2 py-1 rounded-full">
                전환 가능
              </span>
            )}
          </div>
        </div>
      )}

      {/* Completion Badge for Final Stage */}
      {currentStage.stage_number === 6 && progressPercentage >= 80 && (
        <div className="mt-3 pt-3 border-t border-green-200">
          <div className="flex items-center justify-center text-sm font-semibold text-green-700">
            <svg
              className="w-5 h-5 text-green-600 mr-2"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            상담이 성공적으로 완료되었습니다
          </div>
        </div>
      )}
    </div>
  )
}
