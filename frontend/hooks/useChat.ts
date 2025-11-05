/**
 * useChat Hook - Manages chat state and streaming
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import type { Message, RiskLevel, UseChatOptions, UseChatReturn } from '@/types/chat'
import { streamChatMessage } from '@/lib/api'
import {
  getSessionToken,
  getConversationId,
  saveConversationId,
  clearConversation as clearConversationStorage,
} from '@/lib/auth'

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [sessionToken, setSessionToken] = useState<string>('')
  const [conversationId, setConversationId] = useState<string | null>(
    options.conversationId ?? null
  )
  const [crisisDetected, setCrisisDetected] = useState(false)
  const [riskLevel, setRiskLevel] = useState<RiskLevel>('none')

  const messagesRef = useRef(messages)
  messagesRef.current = messages

  // Initialize session token
  useEffect(() => {
    const initSession = async () => {
      try {
        const token = await getSessionToken()
        setSessionToken(token)

        // Load saved conversation ID if not provided in options
        if (!options.conversationId) {
          const savedConversationId = getConversationId()
          if (savedConversationId) {
            setConversationId(savedConversationId)
          }
        }
      } catch (err) {
        console.error('Failed to initialize session:', err)
        setError(err instanceof Error ? err : new Error('Session initialization failed'))
      }
    }

    initSession()
  }, [options.conversationId])

  // Send message
  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading || !sessionToken) {
        console.warn('Cannot send message:', { content, isLoading, sessionToken })
        return
      }

      // Add user message immediately
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: content.trim(),
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, userMessage])
      setIsLoading(true)
      setError(null)

      // Create placeholder for assistant response
      const assistantMessageId = `assistant-${Date.now()}`
      const assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])

      try {
        await streamChatMessage(
          content.trim(),
          sessionToken,
          conversationId,
          // onChunk
          (chunk: string) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, content: msg.content + chunk }
                  : msg
              )
            )
          },
          // onComplete
          (newConversationId: string, crisis: boolean) => {
            setIsLoading(false)

            if (newConversationId && newConversationId !== conversationId) {
              setConversationId(newConversationId)
              saveConversationId(newConversationId)
            }

            if (crisis) {
              setCrisisDetected(true)
              setRiskLevel('high') // Default to high if crisis detected
              options.onCrisisDetected?.({
                risk_level: 'high',
                reasoning: 'Crisis detected in conversation',
                immediate_action_needed: true,
                suggested_resources: ['1393', '119'],
                confidence: 0.8,
                detected_keywords: [],
              })
            }
          },
          // onError
          (err: Error) => {
            setIsLoading(false)
            setError(err)
            console.error('Chat error:', err)

            // Update assistant message with error
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? {
                      ...msg,
                      content: '죄송합니다. 오류가 발생했습니다. 다시 시도해 주세요.',
                    }
                  : msg
              )
            )

            options.onError?.(err)
          }
        )
      } catch (err) {
        setIsLoading(false)
        const error = err instanceof Error ? err : new Error('Unknown error')
        setError(error)
        console.error('Failed to send message:', err)
        options.onError?.(error)
      }
    },
    [isLoading, sessionToken, conversationId, options]
  )

  // Clear messages and start new conversation
  const clearMessages = useCallback(() => {
    setMessages([])
    setConversationId(null)
    setCrisisDetected(false)
    setRiskLevel('none')
    setError(null)
    clearConversationStorage()
  }, [])

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    conversationId,
    crisisDetected,
    riskLevel,
  }
}
