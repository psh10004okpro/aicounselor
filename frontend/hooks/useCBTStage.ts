/**
 * Hook for managing CBT stage information
 */

import { useState, useEffect, useCallback } from 'react'
import { getCBTStage } from '@/lib/api-client'
import type { CBTStageInfo, CBTStage, CBTProgress } from '@/types/chat'

interface UseCBTStageOptions {
  conversationId: string | null
  enabled?: boolean
  refreshInterval?: number
}

interface UseCBTStageReturn {
  currentStage: CBTStage | null
  progress: CBTProgress | null
  isLoading: boolean
  error: Error | null
  refresh: () => Promise<void>
}

/**
 * Hook for managing CBT stage information
 *
 * @param options - Configuration options
 * @returns CBT stage state and functions
 */
export function useCBTStage({
  conversationId,
  enabled = true,
  refreshInterval,
}: UseCBTStageOptions): UseCBTStageReturn {
  const [currentStage, setCurrentStage] = useState<CBTStage | null>(null)
  const [progress, setProgress] = useState<CBTProgress | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const fetchStage = useCallback(async () => {
    if (!conversationId || !enabled) {
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const data: CBTStageInfo = await getCBTStage(conversationId)

      if (data.success) {
        setCurrentStage(data.current_stage)
        setProgress(data.progress)
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch CBT stage'))
      console.error('Error fetching CBT stage:', err)
    } finally {
      setIsLoading(false)
    }
  }, [conversationId, enabled])

  // Initial fetch and refresh on conversationId change
  useEffect(() => {
    fetchStage()
  }, [fetchStage])

  // Optional polling for real-time updates
  useEffect(() => {
    if (!refreshInterval || !conversationId || !enabled) {
      return
    }

    const interval = setInterval(fetchStage, refreshInterval)
    return () => clearInterval(interval)
  }, [fetchStage, refreshInterval, conversationId, enabled])

  return {
    currentStage,
    progress,
    isLoading,
    error,
    refresh: fetchStage,
  }
}
