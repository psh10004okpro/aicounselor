'use client'

import { useEffect, useRef, useState } from 'react'
import type { Message } from '@/types/chat'

interface MessageBubbleProps {
  message: Message
  isLatest?: boolean
}

export default function MessageBubble({ message, isLatest = false }: MessageBubbleProps) {
  const messageRef = useRef<HTMLDivElement>(null)
  const [isVisible, setIsVisible] = useState(false)
  const isUser = message.role === 'user'
  const isAssistant = message.role === 'assistant'

  useEffect(() => {
    // Add fade-in animation
    const timer = setTimeout(() => setIsVisible(true), 50)
    return () => clearTimeout(timer)
  }, [])

  const formatTime = (date: Date) => {
    return new Date(date).toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div
      ref={messageRef}
      className={`flex items-start space-x-2 ${isUser ? 'flex-row-reverse space-x-reverse' : ''} transition-all duration-300 ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'
      }`}
    >
      {/* Avatar */}
      {isAssistant && (
        <div className="w-8 h-8 rounded-full bg-counselor-main flex items-center justify-center text-white text-sm font-medium flex-shrink-0">
          마
        </div>
      )}

      {/* Message bubble */}
      <div className="flex flex-col max-w-[75%] md:max-w-[65%]">
        <div
          className={`rounded-2xl px-4 py-3 shadow-sm ${
            isUser
              ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-br-sm'
              : message.crisisDetected
              ? 'bg-red-50 text-gray-800 border-2 border-red-300 rounded-bl-sm'
              : 'bg-gray-100 text-gray-800 rounded-bl-sm'
          }`}
        >
          {/* Message content */}
          <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">
            {message.content || <TypingCursor />}
          </div>

          {/* Crisis badge */}
          {message.crisisDetected && (
            <div className="mt-2 flex items-center text-xs text-red-700 font-medium">
              <svg
                className="w-4 h-4 mr-1"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
              위기 지원 정보 제공
            </div>
          )}

          {/* Detected keywords (for debugging, optional) */}
          {message.detectedKeywords && message.detectedKeywords.length > 0 && (
            <div className="mt-2 text-xs text-gray-600">
              <span className="font-medium">감지된 키워드:</span>{' '}
              {message.detectedKeywords.join(', ')}
            </div>
          )}
        </div>

        {/* Timestamp and status */}
        <div className={`flex items-center space-x-2 mt-1 px-2 ${isUser ? 'justify-end' : 'justify-start'}`}>
          <span className="text-xs text-gray-400">
            {formatTime(message.timestamp)}
          </span>
          {isUser && isLatest && (
            <span className="text-xs text-green-500">✓</span>
          )}
        </div>
      </div>

      {/* User avatar placeholder */}
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm font-medium flex-shrink-0">
          나
        </div>
      )}
    </div>
  )
}

function TypingCursor() {
  return (
    <span className="inline-block w-0.5 h-4 bg-gray-400 animate-pulse ml-0.5" />
  )
}
