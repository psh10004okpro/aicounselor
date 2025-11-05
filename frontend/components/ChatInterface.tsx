'use client'

import { useState, useRef, useEffect } from 'react'
import { Message } from '@/lib/api'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import CrisisAlert from './CrisisAlert'
import {
  streamChatMessage,
  getSessionToken,
  getConversationId,
  saveConversationId,
  clearConversation,
} from '@/lib/api'

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [sessionToken] = useState(() => getSessionToken())
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [crisisDetected, setCrisisDetected] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Load conversation ID on mount
  useEffect(() => {
    const savedConversationId = getConversationId()
    if (savedConversationId) {
      setConversationId(savedConversationId)
    }
  }, [])

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    // Create placeholder for assistant response
    const assistantMessageId = (Date.now() + 1).toString()
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, assistantMessage])

    try {
      await streamChatMessage(
        content,
        sessionToken,
        conversationId,
        // On chunk received
        (chunk: string) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: msg.content + chunk }
                : msg
            )
          )
        },
        // On complete
        (newConversationId: string, crisis: boolean) => {
          setIsLoading(false)
          if (newConversationId && newConversationId !== conversationId) {
            setConversationId(newConversationId)
            saveConversationId(newConversationId)
          }
          if (crisis) {
            setCrisisDetected(true)
          }
        },
        // On error
        (error: Error) => {
          setIsLoading(false)
          console.error('Chat error:', error)
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    content:
                      'Sorry, I encountered an error. Please try again.',
                  }
                : msg
            )
          )
        }
      )
    } catch (error) {
      setIsLoading(false)
      console.error('Chat error:', error)
    }
  }

  const handleNewConversation = () => {
    setMessages([])
    setConversationId(null)
    setCrisisDetected(false)
    clearConversation()
  }

  return (
    <div className="flex flex-col h-[600px] bg-white rounded-lg shadow-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 bg-counselor-main text-white">
        <div>
          <h2 className="text-xl font-semibold">Chat Session</h2>
          <p className="text-sm text-green-100">
            {conversationId ? 'Conversation in progress' : 'Start a new conversation'}
          </p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={handleNewConversation}
            className="px-4 py-2 bg-white text-counselor-main rounded-lg hover:bg-green-50 transition-colors"
          >
            New Chat
          </button>
        )}
      </div>

      {/* Crisis Alert */}
      {crisisDetected && <CrisisAlert />}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 px-8">
            <svg
              className="w-16 h-16 mb-4 text-counselor-main"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
              />
            </svg>
            <h3 className="text-lg font-medium mb-2">Welcome!</h3>
            <p className="text-center text-sm max-w-md">
              I'm here to listen and provide support. Feel free to share
              what's on your mind. Everything you share is private and
              confidential.
            </p>
          </div>
        ) : (
          <MessageList messages={messages} isLoading={isLoading} />
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <MessageInput onSend={handleSendMessage} disabled={isLoading} />
    </div>
  )
}
