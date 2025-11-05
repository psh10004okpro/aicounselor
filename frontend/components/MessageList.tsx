'use client'

import { useEffect, useRef } from 'react'
import type { Message } from '@/types/chat'
import MessageBubble from './MessageBubble'
import { TypingIndicator } from './LoadingDots'

interface MessageListProps {
  messages: Message[]
  isLoading: boolean
}

export default function MessageList({ messages, isLoading }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [messages])

  return (
    <div className="px-6 py-4 space-y-4">
      {messages.length === 0 && !isLoading && (
        <div className="text-center text-gray-400 py-8">
          <p className="text-sm">대화를 시작해보세요</p>
        </div>
      )}

      {messages.map((message, index) => (
        <MessageBubble
          key={message.id}
          message={message}
          isLatest={index === messages.length - 1}
        />
      ))}

      {isLoading && (
        <div className="flex items-start space-x-2">
          <div className="w-8 h-8 rounded-full bg-counselor-main flex items-center justify-center text-white text-sm font-medium flex-shrink-0">
            마
          </div>
          <TypingIndicator />
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
